#!/usr/bin/env python3
"""
Скрипт подання завдання Ray
Подає ray_job.py як завдання Ray з завантаженням файлів
"""

import os
import tempfile
import ray
import yaml
import logging
from pathlib import Path
from datetime import datetime
import subprocess
import sys

# Зменшуємо детальність логування Ray
logging.getLogger("ray").setLevel(logging.WARNING)

# Завантажуємо змінні середовища з .env файлу
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Loaded environment variables from .env")
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Or set environment variables manually")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")


def load_config(config_path="config.yaml"):
    """Завантажує конфігурацію з YAML файлу"""
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        print(f"⚠️  Could not load config file: {e}")
        return None


def check_required_files():
    """Перевіряє, чи існують всі необхідні файли"""
    required_files = ["train_yolo.py", "config.yaml", "requirements.txt", "ray_job.py", "../dataset.tar.gz",
                      "data.yaml"]
    missing_files = [f for f in required_files if not Path(f).exists()]

    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False

    print("✅ All required files found")
    return True


def prepare_job_files():
    root = Path.cwd()
    files_to_upload = [
        "train_yolo.py",
        "config.yaml",
        "requirements.txt",
        "ray_job.py",
        "data.yaml",
        "../dataset.tar.gz",  # якщо запущено з yolo-cpu, або просто "dataset" при запуску з кореня
    ]
    file_contents = {}

    for entry in files_to_upload:
        p = root / entry
        if not p.exists():
            print(f"❌ Missing required file or folder: {entry}")
            return None

        if p.is_dir():
            # рекурсивно додаємо всі файли з папки
            for f in p.rglob("*"):
                if f.is_file():
                    # відносний шлях від кореня проєкту, у POSIX-форматі
                    rel = f.relative_to(root).as_posix()
                    file_contents[rel] = f.read_bytes()
                    print(f"  ✅ Prepared {rel}")
        else:
            # одиночний файл (скрипт або yaml)
            rel = p.relative_to(root).name
            file_contents[rel] = p.read_bytes()
            print(f"  ✅ Prepared {rel}")

    return file_contents


@ray.remote
def run_ray_job(file_contents):
    # 1. Створюємо тимчасову робочу папку і переходимо в неї
    tmp_dir = tempfile.mkdtemp()
    os.chdir(tmp_dir)

    # 2. Розпаковуємо код і конфіги
    for rel_path, content in file_contents.items():
        # Приводимо шлях до POSIX-формату і прибираємо "../" якщо потрібно
        clean_rel = Path(rel_path).as_posix().lstrip("../")
        p = Path(clean_rel)
        if p.parent != Path("."):
            p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.write(content)

    # 3. Для відлагодження — виводимо, що у нас всередині
    print("📁 Files before dataset unpack:")
    for p in sorted(Path(".").rglob("*")):
        print(" -", p)

    # 4. *** РОЗПАКУВАННЯ ДАТАСЕТУ З ОДНОГО АРХІВУ ***
    #    Замість того, щоб тягнути весь каталог dataset по файлику,
    #    ми вантажимо тільки dataset.tar.gz і розпаковуємо його.
    print("🔧 Розпаковуємо датасет з архіву dataset.tar.gz …")
    subprocess.run(["tar", "xzf", "dataset.tar.gz"], check=True)

    # 5. Знову виводимо вміст — тепер з dataset/
    print("📁 Files after dataset unpack:")
    for p in sorted(Path(".").rglob("*")):
        print(" -", p)

    # Змінні середовища тепер встановлюються через runtime_env
    print("✅ Files uploaded and environment configured")

    # Запускаємо ray_job.py
    try:
        result = subprocess.run([sys.executable, "ray_job.py"],
                                capture_output=True, text=True, check=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ ray_job.py failed: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def main():
    """Головна функція"""
    print("🚀 Ray Task Submission for YOLO Training")
    print("=" * 40)

    # Адреса кластера Ray
    ray_address = "ray://localhost:10001"  # Адреса кластера Ray

    # Перевіряємо необхідні файли
    if not check_required_files():
        return

    # Збираємо змінні середовища W&B
    wandb_env = {
        'WANDB_API_KEY': os.getenv('WANDB_API_KEY'),
        'WANDB_PROJECT': os.getenv('WANDB_PROJECT'),
        'WANDB_ENTITY': os.getenv('WANDB_ENTITY')
    }

    # Перевіряємо конфігурацію W&B (не показуючи значення)
    print("🔑 W&B Environment Variables:")
    for key, value in wandb_env.items():
        if value:
            print(f"   ✅ {key} is set")
        else:
            print(f"   ⚠️  {key} not set")

    if not wandb_env['WANDB_API_KEY']:
        print("\n⚠️  WANDB_API_KEY is required!")
        print("   Set it with: export WANDB_API_KEY=your_key")
        print("   Or get it from: https://wandb.ai/authorize")

    # Ініціалізуємо Ray
    try:
        if not ray.is_initialized():
            ray.init(address=ray_address)
            print(f"✅ Connected to Ray cluster at {ray_address}")
            print("-" * 40)  # Роздільник після логів підключення Ray
            print("Available resources:", ray.available_resources())
    except Exception as e:
        print(f"❌ Cannot connect to Ray cluster at {ray_address}: {e}")
        print("   Make sure Ray cluster is running:")
        print("   ray start --head --dashboard-host=0.0.0.0 --dashboard-port=8265")
        return

    try:
        # Підготовляємо файли
        print("📁 Preparing files...")
        file_contents = prepare_job_files()
        if not file_contents:
            return

        # Подаємо завдання
        print("🚀 Submitting ray_job.py as Ray task...")

        # Завантажуємо конфігурацію для отримання базової назви запуску
        config = load_config()
        base_run_name = config.get('run_name', 'yolo-ray-training') if config else 'yolo-ray-training'

        # Генеруємо динамічну назву запуску з часовою міткою
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        run_name = f"{base_run_name}-{timestamp}"

        # Підготовляємо середовище виконання зі змінними W&B
        env_vars = {k: v for k, v in wandb_env.items() if v}  # Лише непорожні значення
        env_vars['WANDB_RUN_NAME'] = run_name  # Додаємо динамічну назву запуску

        runtime_env = {
            "env_vars": env_vars
        }

        print(f"📋 Runtime environment: {len(runtime_env['env_vars'])} variables")
        print(f"🏃 Run name: {run_name}")
        for key in runtime_env['env_vars'].keys():
            if key != 'WANDB_API_KEY':  # Не показуємо API ключ
                print(f"   - {key}")
            else:
                print(f"   - {key} (hidden)")

        if not runtime_env['env_vars']:
            print("⚠️  No environment variables to pass!")
            print("   Make sure .env file exists or variables are exported")

        # Подаємо завдання з середовищем виконання
        task = run_ray_job.options(runtime_env=runtime_env).remote(file_contents)

        # Чекаємо завершення
        print("👀 Waiting for task completion...")
        success = ray.get(task)

        if success:
            print("🎉 Training completed successfully!")
            print("🌐 Check results at:")
            print("   - Ray Dashboard: http://localhost:8265")
            print("   - W&B Dashboard: https://wandb.ai")
        else:
            print("❌ Training failed")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        ray.shutdown()
        print("🔌 Ray connection closed")


if __name__ == "__main__":
    main()
