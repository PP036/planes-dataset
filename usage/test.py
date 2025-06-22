import cv2
import numpy as np
import requests
import json

image_url = "https://img.flytrippers.com/wp-content/uploads/2024/01/11131250/How-to-see-what-type-of-aircraft-your-flight-operates.jpg"
server_url = "http://localhost:8000/detect"

resp = requests.get(image_url)
image_nparray = np.asarray(bytearray(resp.content), dtype=np.uint8)
image = cv2.imdecode(image_nparray, cv2.IMREAD_COLOR)

resp = requests.get(f"{server_url}?image_url={image_url}")

print("Response status code:", resp.status_code)
print("Response JSON:", resp.json())

try:
    response_json = resp.json()
    detections = response_json.get("objects", [])
    if not detections:
        print("❌ У відповіді немає об'єктів. Відповідь:", response_json)
except json.decoder.JSONDecodeError:
    print("❌ Не вдалося декодувати JSON. Відповідь:", resp.text)
    detections = []

for item in detections:
    class_name = item["class"]
    coords = item["coordinates"]

    cv2.rectangle(image, (int(coords[0]), int(coords[1])), (int(coords[2]), int(coords[3])), (0, 0, 0), 2)

    cv2.putText(image, class_name, (int(coords[0]), int(coords[1] - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

cv2.imwrite("output.jpeg", image)