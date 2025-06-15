import os
import shutil
import random


BASE_DIR = "dataset"
IMAGES_DIR = os.path.join(BASE_DIR, "images")
LABELS_DIR = os.path.join(BASE_DIR, "labels")

for subfolder in ["train", "val"]:
    os.makedirs(os.path.join(IMAGES_DIR, subfolder), exist_ok=True)
    os.makedirs(os.path.join(LABELS_DIR, subfolder), exist_ok=True)

image_files = [f for f in os.listdir(IMAGES_DIR) if f.endswith(".jpg")]
image_files.sort()

random.shuffle(image_files)
split_idx = int(0.8 * len(image_files))
train_files = image_files[:split_idx]
val_files = image_files[split_idx:]


def move_files(file_list, split):
    for image_name in file_list:
        label_name = image_name.replace(".jpg", ".txt")

        src_img = os.path.join(IMAGES_DIR, image_name)
        src_lbl = os.path.join(LABELS_DIR, label_name)

        dst_img = os.path.join(IMAGES_DIR, split, image_name)
        dst_lbl = os.path.join(LABELS_DIR, split, label_name)

        if os.path.exists(src_img):
            shutil.move(src_img, dst_img)
        if os.path.exists(src_lbl):
            shutil.move(src_lbl, dst_lbl)


move_files(train_files, "train")
move_files(val_files, "val")

print("✅ Dataset успешно разделён на train и val.")
