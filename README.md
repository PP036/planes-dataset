# Підготовка даних

## Налаштування інструментів для роботи з датасетом

1. Перейдіть до директорії docker:
   ```bash
   cd docker
   ```

2. Запустіть Docker Compose для встановлення необхідних інструментів:
   ```bash
   docker compose up -d
   ```

## Робота з зображеннями та розмітка

1. Додайте зображення до `planes-dataset`
2. Синхронізуйте з Label Studio
3. Виконайте розмітку зображень
4. Запустіть скрипт експорту у формат YOLO:
   ```bash
   ./export-yolo.sh
   ```

## Підготовка фінального датасету

1. Перейдіть до директорії датасету:
   ```bash
   cd dataset
   ```

2. Розпакуйте архів з експортованими даними:
   ```bash
   unzip yolo_export.zip
   ```

3. Запустіть скрипт для перейменування міток:
   ```bash
   python rename-labels.py
   ```

4. Перемістіть вибрані зображення з Kaggle до вашого датасету:
   ```bash
   # Переміщення зображень з джерела до цільової директорії
   mv kaggle-dataset/planes_v2/* dataset/images/
   ```

5. Розділіть дані на навчальну та тестову вибірки:
   ```bash
   python split-data.py
   ```

✅ **Датасет готовий до використання!**

# Тренування моделі

## Налаштування кластеру

1. Перейдіть до директорії k8s:
   ```bash
   cd k8s
   ```

2. Запустіть скрипт налаштування кластеру:
   ```bash
   ./setup-cluster.sh
   ```

3. Після успішного налаштування ви отримаєте доступ до наступних ресурсів:
   - **Ray Dashboard**: [http://localhost:8265](http://localhost:8265)
   - **Ray Client API**: ray://localhost:10001
   - **Prometheus**: [http://localhost:9090](http://localhost:9090)
   - **Grafana**: [http://localhost:3000](http://localhost:3000) 
     - Логін: `admin`
     - Пароль: `prom-operator`

## Запуск тренування

1. Перейдіть до директорії train-model:
   ```bash
   cd train-model
   ```

2. Налаштуйте змінні середовища для Weights & Biases у файлі `.env`:
   ```bash
   WANDB_API_KEY=your_api_key
   WANDB_PROJECT=your_project_name
   WANDB_ENTITY=your_entity
   WANDB_MODEL_ARTIFACT=your_model_artifact
   ```

3. Завантажте підготовлений датасет у кластер та запустіть тренування:
   ```bash
   python submit_job.py
   ```

## Моніторинг тренування

1. Відкрийте [Weights & Biases](https://wandb.ai) у браузері для перегляду прогресу тренування
2. Використовуйте Ray Dashboard для моніторингу ресурсів кластеру
3. При необхідності перевіряйте метрики у Prometheus та Grafana

✅ **Процес тренування запущено та відстежується!**
    
# Використання моделі

## Запуск сервісу моделі

1. Перейдіть до директорії з кодом для використання моделі:
   ```bash
   cd usage
   ```

2. Запустіть скрипт сервінгу моделі:
   ```bash
   python run_serve.py
   ```

3. Налаштуйте переадресацію портів для доступу до сервісу:
   ```bash
   kubectl port-forward service/raycluster-kuberay-head-svc 8000:8000
   ```

## Перевірка роботи сервісу

1. Відкрийте документацію API за адресою:
   [http://localhost:8000/docs](http://localhost:8000/docs)

## Тестування детекції об'єктів

Використовуйте клієнтський скрипт для детекції об'єктів на зображеннях:

### З локальних файлів:
```bash
python client.py images/test.jpg
```

### З зображень за URL:
```bash
python client.py https://img.flytrippers.com/wp-content/uploads/2024/01/11131250/How-to-see-what-type-of-aircraft-your-flight-operates.jpg
```

✅ **Модель готова до використання!**



