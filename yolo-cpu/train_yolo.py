#!/usr/bin/env python3
"""
Скрипт тренування YOLOv8n з інтеграцією Weights & Biases
Тренує модель YOLOv8n на CPU з трекінгом W&B та збереженням чекпоінтів
"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from ultralytics import YOLO
import torch


def load_config(config_path: str = "config.yaml") -> dict:
    """Завантажує конфігурацію з YAML файлу"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def setup_wandb():
    """Налаштування W&B, логін та активація інтеграції"""
    load_dotenv()
    wandb_key = os.getenv('WANDB_API_KEY')
    if wandb_key:
        try:
            import wandb
            wandb.login(key=wandb_key)
            from ultralytics.utils import SETTINGS
            SETTINGS['wandb'] = True
            print("✅ W&B інтеграцію увімкнено")
        except Exception as e:
            print(f"⚠️  Не вдалося налаштувати W&B: {e}")
    else:
        print("⚠️  WANDB_API_KEY не знайдено, W&B вимкнено")


def train(config: dict):
    """Запуск тренування YOLO за параметрами з конфіг-файлу"""
    # Примусово CPU
    config['device'] = 'cpu'
    run_name = os.getenv('WANDB_RUN_NAME', config.get('run_name'))

    print("🚀 Початок тренування YOLOv8n на пристрої:", config['device'])
    print(f"📦 Модель: {config['model']}")
    print(f"📋 Дані: {config['data']}")
    print(f"📆 Епохи: {config['epochs']}, batch: {config['batch']}")

    model = YOLO(config['model'])
    results = model.train(
        data=config['data'],
        epochs=config['epochs'],
        batch=config['batch'],
        imgsz=config['imgsz'],
        device=config['device'],
        workers=config['workers'],
        optimizer=config['optimizer'],
        lr0=config['lr0'],
        momentum=config['momentum'],
        weight_decay=config['weight_decay'],
        save=config['save'],
        save_period=config['save_period'],
        project=config['wandb_project'],
        name=run_name,
        plots=True,
        verbose=True
    )
    print("✅ Тренування завершено")
    return results


def main():
    print("" + "=" * 50)
    print("🤖 YOLOv8n CPU Training with W&B")
    print("" + "=" * 50)
    try:
        cfg = load_config()
        setup_wandb()
        train(cfg)
    except Exception as e:
        print(f"❌ Помилка: {e}")
        raise


if __name__ == '__main__':
    main()