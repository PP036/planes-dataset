import requests
import sys
import json
import cv2
import os
import numpy as np
from pathlib import Path
from urllib.parse import urlparse

API_URL = "http://localhost:30080"


def check_health():
    """Перевірка стану API"""
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Статус API: {data['status']}")
            print(f"   Модель: {data['model']}")
            return True
        else:
            print(f"❌ Перевірка стану не вдалася: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Помилка з'єднання: {e}")
        return False


def download_image_from_url(url):
    """Завантаження зображення за URL"""
    try:
        print(f"📥 Завантаження зображення з URL...")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        # Конвертація в numpy array для OpenCV
        image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            print(f"❌ Не вдалося декодувати зображення з URL")
            return None

        print(f"✅ Зображення успішно завантажено")
        return image, response.content

    except Exception as e:
        print(f"❌ Помилка завантаження зображення: {e}")
        return None, None


def draw_detections(image, detections, output_path):
    """Малювання bbox'ів на зображенні"""
    try:
        # Кольори для різних класів (BGR format)
        colors = [
            (0, 255, 0),  # Зелений
            (255, 0, 0),  # Синій
            (0, 0, 255),  # Червоний
            (255, 255, 0),  # Блакитний
            (255, 0, 255),  # Пурпуровий
            (0, 255, 255),  # Жовтий
        ]

        # Створюємо копію зображення для анотацій
        annotated_image = image.copy()

        # Малювання кожного detection
        for i, detection in enumerate(detections):
            bbox = detection['bbox']
            class_name = detection['class_name']
            confidence = detection['confidence']

            # Координати bbox
            x1, y1, x2, y2 = map(int, bbox)

            # Вибір кольору
            color = colors[i % len(colors)]

            # Малювання прямокутника
            cv2.rectangle(annotated_image, (x1, y1), (x2, y2), color, 2)

            # Підготовка тексту
            label = f"{class_name}: {confidence:.2f}"

            # Розмір тексту
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            (text_width, text_height), _ = cv2.getTextSize(label, font, font_scale, thickness)

            # Фон для тексту
            cv2.rectangle(annotated_image, (x1, y1 - text_height - 10), (x1 + text_width, y1), color, -1)

            # Текст
            cv2.putText(annotated_image, label, (x1, y1 - 5), font, font_scale, (255, 255, 255), thickness)

        # Збереження результату
        cv2.imwrite(output_path, annotated_image)
        print(f"📸 Анотоване зображення збережено: {output_path}")
        return True

    except Exception as e:
        print(f"❌ Помилка малювання детекцій: {e}")
        return False


def detect_objects_from_url(url):
    """Завантаження зображення за URL та відправка на детекцію"""
    try:
        # Завантаження зображення
        image, image_bytes = download_image_from_url(url)
        if image is None or image_bytes is None:
            return None, None

        # Відправка на API
        print(f"🔍 Відправлення зображення до API...")
        files = {'file': ('image.jpg', image_bytes, 'image/jpeg')}
        response = requests.post(f"{API_URL}/detect", files=files)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Детекція завершена!")
            print(f"   Час обробки: {data['processing_time_ms']:.1f}мс")
            print(f"   Виявлено об'єктів: {data['objects_detected']}")

            # Показуємо всі детекції
            if data['detections']:
                print(f"\n🔍 Виявлені об'єкти:")
                for i, detection in enumerate(data['detections'], 1):
                    bbox = detection['bbox']
                    print(f"   {i}. {detection['class_name']}: {detection['confidence']:.3f}")
                    print(f"      bbox: [{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]")

            return data, image
        else:
            print(f"❌ Детекція не вдалася: {response.status_code}")
            print(f"   Помилка: {response.text}")
            return None, None

    except Exception as e:
        print(f"❌ Помилка: {e}")
        return None, None


def is_url(string):
    """Перевірка, чи є рядок URL-адресою"""
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except:
        return False


def detect_objects_from_local_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            image_bytes = f.read()

        image = cv2.imread(file_path)
        if image is None:
            print("❌ Неможливо прочитати зображення")
            return None, None

        print(f"🔍 Відправлення локального зображення до API...")
        files = {'file': (os.path.basename(file_path), image_bytes, 'image/jpeg')}
        response = requests.post(f"{API_URL}/detect", files=files)

        if response.status_code == 200:
            data = response.json()
            return data, image
        else:
            print(f"❌ Помилка: {response.status_code} {response.text}")
            return None, None

    except Exception as e:
        print(f"❌ Виняток: {e}")
        return None, None


def main():
    if len(sys.argv) != 2:
        print("Використання: python client.py <URL_або_шлях_до_зображення>")
        print("Приклад: python client.py https://ultralytics.com/images/bus.jpg")
        print("Приклад: python client.py planes/0076782.jpg")
        sys.exit(1)

    image_input = sys.argv[1]

    if not is_url(image_input) and not os.path.isfile(image_input):
        print(f"❌ Файл або URL не знайдено: {image_input}")
        sys.exit(1)

    print("🚀 Клієнт детекції YOLO11")
    print("=" * 40)

    if not check_health():
        print("💡 Переконайтеся, що API запущено: python app.py")
        sys.exit(1)

    print()

    # Виклик відповідної функції
    if is_url(image_input):
        result, image = detect_objects_from_url(image_input)
        filename = os.path.basename(urlparse(image_input).path) or "image.jpg"
    else:
        result, image = detect_objects_from_local_file(image_input)
        filename = os.path.basename(image_input)

    if result and result['detections'] and image is not None:
        print(f"\n📄 Повна відповідь:")
        print(json.dumps(result, indent=2))

        output_path = f"{Path(filename).stem}_detected{Path(filename).suffix}"
        if draw_detections(image, result['detections'], output_path):
            print(f"✨ Готово! Перевірте анотоване зображення: {output_path}")
    elif result and result['objects_detected'] == 0:
        print("ℹ️  Об'єктів не виявлено на зображенні")
    else:
        print("❌ Детекція не вдалася або немає результатів")


if __name__ == "__main__":
    main()