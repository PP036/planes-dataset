import requests
import sys
import cv2
import os
import numpy as np
from pathlib import Path
from urllib.parse import urlparse

SERVER_URL = "http://localhost:8000"
INPUT_DIR = "images/input"
OUTPUT_DIR = "images/output"

def is_url(string):
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except:
        return False

def detect_from_url(image_url):
    try:
        print(f"🔍 GET: {SERVER_URL}/detect")
        resp = requests.get(f"{SERVER_URL}/detect", params={"image_url": image_url})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"❌ GET помилка: {e}")
        return None

def detect_from_file(file_path):
    try:
        print(f"📤 POST: {SERVER_URL}/detect_file")
        with open(file_path, "rb") as f:
            files = {'file': f}
            resp = requests.post(f"{SERVER_URL}/detect_file", files=files)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        print(f"❌ POST помилка: {e}")
        return None

def draw_boxes(image, detections, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    for det in detections:
        cls = det["class"]
        conf = det.get("confidence", 0)
        x1, y1, x2, y2 = map(int, det["coordinates"])
        label = f"{cls} {conf:.2f}"

        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(image, label, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    cv2.imwrite(output_path, image)
    print(f"📸 Зображення збережено як {output_path}")

def main():
    if len(sys.argv) != 2:
        print("Використання: python client.py <image_url або ім'я_файлу>")
        sys.exit(1)

    input_arg = sys.argv[1]
    input_path = os.path.join(INPUT_DIR, input_arg)
    result = None

    if is_url(input_arg):
        result = detect_from_url(input_arg)
        if result and result.get("objects"):
            resp = requests.get(input_arg)
            img_arr = np.asarray(bytearray(resp.content), dtype=np.uint8)
            image = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            output_path = os.path.join(OUTPUT_DIR, f"{Path(input_arg).stem}_output.jpg")
            draw_boxes(image, result["objects"], output_path)
    elif os.path.isfile(input_path):
        result = detect_from_file(input_path)
        if result:
            print("✅ Отримано результат:", result)
            if result.get("objects"):
                image = cv2.imread(input_path)
                if image is None:
                    print(f"❌ Не вдалося зчитати зображення: {input_path}")
                    sys.exit(1)
                name_no_ext = Path(input_arg).stem
                output_path = os.path.join(OUTPUT_DIR, f"{name_no_ext}_output.jpg")
                draw_boxes(image, result["objects"], output_path)
            else:
                print("ℹ️ Об'єкти не знайдено на зображенні.")
        else:
            print("❌ Не вдалося отримати результат від сервера.")
    else:
        print("❌ Некоректний шлях або URL")
        sys.exit(1)

if __name__ == "__main__":
    main()
