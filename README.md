# Управління даними

## Локальний запуск Label Studio

```bash
docker compose up -d
```

### Налаштування MinIO

**MINIO:** http://localhost:9009/
- **Логін:** minioadmin
- **Пароль:** minioadmin

Бакети:
- `planes-dataset` - для зберігання вихідних даних (зображення)
- `planes-labeled-dataset` - для зберігання розмічених даних від Label Studio
- `planes-dvc-storage` - для зберігання версіонованих даних через DVC

### Налаштування Label Studio

**Label Studio:** http://localhost:8080/

1. Реєструємо акаунт
2. Створюємо проєкт
   - Обираємо тип: Object Detection with Bounding Boxes

3. Налаштовуємо проєкт
   - Обираємо Cloud Storage
   - Налаштовуємо Source Cloud Storage та Target Cloud Storage:
     - URL: http://minio:9000
     - Опція "Treat every bucket object as a source file" - щоб кожен файл був завданням
     - Вимикаємо pre-signed URLs - для проксювання зображень на фронт

4. Завантажуємо зображення
5. Виконуємо демо розмітки
6. Показуємо приклад для розмітки питання-відповідь


## Версіювання даних

Наш репозиторій для датасету:
https://github.com/PP036/planes-dataset

### Встановлення та налаштування DVC

```bash
# Встановлюємо DVC
pip install 'dvc[all]'

# Ініціалізуємо DVC в проєкті
dvc init

# Створюємо директорію для даних
mkdir -p dataset

# Налаштовуємо віддалене сховище в MinIO
dvc remote add -d storage s3://cars-dvc-storage
dvc remote modify storage endpointurl http://localhost:9000

# Використовуємо змінні середовища для облікових даних
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
dvc remote modify storage --local access_key_id ${MINIO_ACCESS_KEY}
dvc remote modify storage --local secret_access_key ${MINIO_SECRET_KEY}

# Фіксуємо початкову конфігурацію DVC в Git
git add .dvc .gitignore
git commit -m "Ініціалізація DVC та налаштування сховища"
```

### Робота з версіями даних

```bash
# Додаємо дані в DVC
dvc add dataset

# Перевіряємо створені файли
cat dataset.dvc
cat .gitignore

# Додаємо файли в Git та робимо коміт
git add dataset.dvc .gitignore
git commit -m "v1"

# Відправляємо дані у віддалене сховище
dvc push
dvc status
```

### Оновлення даних

```bash
# Робимо ще розмітку та експортуємо нові дані до репозиторія

# Перевіряємо статус
dvc status

# Дивимось що саме змінилось
dvc diff

# Додаємо оновлені дані в DVC
dvc add dataset

# Додаємо файли в Git
git add dataset.dvc

# Фіксуємо зміни
git commit -m "v2"

# Відправляємо дані у віддалене сховище
dvc push
dvc status
```

### Відновлення попередніх версій

```bash
# Відновлюємо попередню версію даних
git log --oneline
git checkout ae49f72
dvc checkout

# Повертаємось до основної гілки
git checkout main
dvc checkout
```

### Клонування та відновлення даних

```bash
# Видаляємо репозиторій
# Клонуємо репозиторій
# Відновлюємо налаштування

# Використовуємо змінні середовища для облікових даних
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
dvc remote modify storage --local access_key_id ${MINIO_ACCESS_KEY}
dvc remote modify storage --local secret_access_key ${MINIO_SECRET_KEY}

# Отримання даних з віддаленого сховища
dvc pull
```