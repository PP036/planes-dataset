import os
import wandb
import tempfile
from ultralytics import YOLO
from fastapi import FastAPI, Request
from fastapi.datastructures import FormData
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile as StarletteUploadFile
from fastapi.datastructures import FormData
import traceback

import ray
from ray import serve
from ray.serve.handle import DeploymentHandle
app = FastAPI()


@serve.deployment(
    num_replicas=1,
    ray_actor_options={"num_cpus": 1}
)
@serve.ingress(app)
class APIIngress:
    def __init__(self, object_detection_handle) -> None:
        self.handle: DeploymentHandle = object_detection_handle.options(use_new_handle_api=True)

    @app.get("/detect")
    async def detect(self, image_url: str):
        result = await self.handle.detect.remote(image_url)
        return JSONResponse(content=result)

    @app.post("/detect_file")
    async def detect_file(self, request: Request):
        print("🚦 [detect_file] Handler triggered")

        try:
            form: FormData = await request.form()
            print("✅ Form data successfully parsed")

            if "file" not in form:
                print("❌ No 'file' in form data keys:", form.keys())
                return JSONResponse(
                    content={"error": "No 'file' field in form data"},
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            file: StarletteUploadFile = form["file"]
            print(f"📁 File name: {file.filename}")
            print(f"📁 Content type: {file.content_type}")

            contents = await file.read()
            print(f"📦 File read completed — size: {len(contents)} bytes")

            if len(contents) == 0:
                print("❌ File is empty")
                return JSONResponse(
                    content={"error": "Uploaded file is empty"},
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(contents)
                tmp_path = tmp.name
                print(f"📄 File written to temp path: {tmp_path}")

            print("🚀 Sending image to object detection handle...")
            result = await self.handle.detect.remote(tmp_path)
            print("✅ Detection completed")

            return JSONResponse(content=result)

        except Exception as e:
            print("❌ Unexpected error in detect_file:")
            traceback.print_exc()
            return JSONResponse(
                content={"error": str(e)},
                status_code=status.HTTP_400_BAD_REQUEST
            )


@serve.deployment(
    autoscaling_config={"min_replicas": 1, "max_replicas": 2},
    ray_actor_options={"num_cpus": 1}
)
class ObjectDetection:
    def __init__(self):
        self.wandb_project = os.getenv("WANDB_PROJECT", "mlops")
        self.wandb_entity = os.getenv("WANDB_ENTITY", "pankratov-set-university")
        self.model_artifact_name = os.getenv(
            "WANDB_MODEL_ARTIFACT",
            "pankratov-set-university/setuniversity-mlops-s25/yolo-model:latest"
        )

        os.environ["WANDB_MODE"] = "online"
        print("🤖 Ініціалізація wandb та завантаження моделі YOLO...")

        run = wandb.init(
            project=self.wandb_project,
            entity=self.wandb_entity,
            job_type="inference",
            mode="online"
        )

        try:
            api_key = os.getenv("WANDB_API_KEY")
            if not api_key:
                raise ValueError("WANDB_API_KEY not found")

            print(f"📥 Завантаження артефакту моделі: {self.model_artifact_name}")
            artifact = run.use_artifact(self.model_artifact_name, type='model')
            model_path = artifact.download()

            model_file = None
            for file in os.listdir(model_path):
                if file.endswith('.pt'):
                    model_file = os.path.join(model_path, file)
                    break

            if model_file is None:
                raise FileNotFoundError("No .pt file in artifact")

            self.model = YOLO(model_file)
            print("✅ Модель успішно завантажена з wandb!")

        except Exception as e:
            print(f"❌ Помилка завантаження моделі з wandb: {e}")
            print("🔄 Завантажуємо резервну модель yolov8n.pt...")
            self.model = YOLO("yolov8n.pt")

        finally:
            wandb.finish()

    async def detect(self, image_input: str):
        conf_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", 0.8))

        # YOLOv8: используем .predict с явным conf
        results = self.model.predict(image_input, conf=conf_threshold)

        detected_objects = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < conf_threshold:
                    continue
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                coords = box.xyxy[0].tolist()

                detected_objects.append({
                    "class": class_name,
                    "coordinates": coords,
                    "confidence": round(conf, 3)
                })

        return {
            "status": "found" if detected_objects else "not found",
            "objects": detected_objects
        }


entrypoint = APIIngress.bind(ObjectDetection.bind())
