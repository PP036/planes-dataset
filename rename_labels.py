import os

folder_path = "dataset/labels"

for filename in os.listdir(folder_path):
    if filename.endswith(".txt") and "__" in filename:
        new_name = filename.split("__", 1)[1]

        old_path = os.path.join(folder_path, filename)
        new_path = os.path.join(folder_path, new_name)

        os.rename(old_path, new_path)
        print(f"Renamed: {filename} → {new_name}")
