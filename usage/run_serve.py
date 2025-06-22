import ray
from ray import serve
import os
from dotenv import load_dotenv

load_dotenv()

ray.init(
    address="ray://localhost:10001",
    runtime_env={
        "working_dir": ".",
        "pip": [
            "ultralytics==8.2.27",
            "wandb==0.16.4",
            "python-dotenv==1.0.1",
            "opencv-python-headless==4.9.0.80",
            "matplotlib==3.8.4",
            "scikit-learn==1.4.2",
            "torch==2.2.2",
            "torchvision==0.17.2",
            "fastapi==0.110.0",               # ⬅️ рабочая версия
            "pydantic==2.6.4",                # ⬅️ рабочая версия
            "pydantic-core==2.16.3",          # ⬅️ рабочая версия
            "ray[serve]==2.46.0",
            "python-multipart==0.0.6"
        ],
        "env_vars": {
            "OPENCV_IO_ENABLE_OPENEXR": "0",
            "OPENCV_IO_ENABLE_JASPER": "0",
            "QT_QPA_PLATFORM": "offscreen",
            "MPLBACKEND": "Agg",
            "WANDB_PROJECT": os.getenv("WANDB_PROJECT", "mlops"),
            "WANDB_ENTITY": os.getenv("WANDB_ENTITY", "pankratov-set-university"),
            "WANDB_MODEL_ARTIFACT": os.getenv("WANDB_MODEL_ARTIFACT",
                                              "pankratov-set-university/setuniversity-mlops-s25/yolo-model:latest"),
            "WANDB_API_KEY": os.getenv("WANDB_API_KEY"),
            "WANDB_MODE": os.getenv("WANDB_MODE", "online"),
            "WANDB_SILENT": "true"
        }
    }
)

from object_detection import entrypoint

serve.run(entrypoint, name="yolo")
