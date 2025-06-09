#!/usr/bin/env python3
from pathlib import Path

labels_dir = Path("dataset/labels")
for txt in labels_dir.glob("*.txt"):
    parts = txt.stem.split("__", 2)

    if len(parts) == 3:
        new_stem = f"{parts[1]}__{parts[2]}"
        new_name = new_stem + ".txt"
        new_path = labels_dir / new_name
        if new_path.exists():
            print(f"SKIP {txt.name} → {new_name} (уже есть)")
        else:
            print(f"REN {txt.name} → {new_name}")
            txt.rename(new_path)
    else:
        print(f"SKIP {txt.name} (непонятный формат)")