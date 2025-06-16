import os
from pathlib import Path

# Путь к датасету
DATASET_DIR = Path("dataset")
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


def check_yolo_annotation_format(label_path):
    with open(label_path, "r") as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            parts = line.strip().split()
            if len(parts) != 5:
                return f"❌ Строка {idx + 1} не содержит 5 элементов: {line.strip()}"
            try:
                cls, x, y, w, h = map(float, parts)
                if not (0 <= cls) or not (0 <= x <= 1) or not (0 <= y <= 1) or not (0 <= w <= 1) or not (0 <= h <= 1):
                    return f"❌ Неверные значения в строке {idx + 1}: {line.strip()}"
            except ValueError:
                return f"❌ Не удалось преобразовать значения в строке {idx + 1}: {line.strip()}"
    return "✅"


def check_dataset_subset(subset):
    image_dir = DATASET_DIR / "images" / subset
    label_dir = DATASET_DIR / "labels" / subset

    images = [f for f in image_dir.glob("*") if f.suffix.lower() in IMAGE_EXTS]

    for img_path in images:
        label_path = label_dir / (img_path.stem + ".txt")

        if not label_path.exists():
            continue

        result = check_yolo_annotation_format(label_path)
        if result != "✅":
            print(f"❌ Ошибка в {label_path.name}: {result}")
        else:
            print(f"✅ {img_path.name} / {label_path.name}")


def main():
    check_dataset_subset("train")
    check_dataset_subset("val")


if __name__ == "__main__":
    main()
