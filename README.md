# Aircraft Detection System for Satellite Imagery

## 1. Project Overview
This project is a system for detecting aircraft in satellite imagery using computer vision and deep learning. It includes the complete data workflow: from dataset management to model training on a distributed cluster and monitoring results.

## 2. Repository Structure
- **`kaggle_data/`** - Original dataset from Kaggle platform
- **`dataset/`** - Prepared dataset for model training
    - `train/` - Training data (80%)
    - `test/` - Testing data (20%)
    - `data.yaml` - YOLO configuration file
- **`k8s/`** - Kubernetes configuration files
- **`docker/`** - Docker-related resources
- **`yolo-cpu/`** - YOLO scripts for CPU-based inference

## 3. Local Environment Setup

### 3.1 Label Studio Setup
```bash
# Launch Label Studio and MinIO containers
docker compose up -d
```

### 3.2 MinIO Configuration
- **URL:** http://localhost:9009/
- **Credentials:** minioadmin / minioadmin
- **Required Buckets:**
    - `planes-dataset` - Source images
    - `planes-labeled-dataset` - Labeled data from Label Studio
    - `planes-dvc-storage` - DVC data versioning storage

### 3.3 Label Studio Configuration
- **URL:** http://localhost:8080/
- **Setup Steps:**
    1. Register an account
    2. Create a project (Object Detection with Bounding Boxes)
    3. Configure cloud storage:
        - URL: http://minio:9000
        - Enable "Treat every bucket object as a source file"
        - Disable pre-signed URLs
    4. Upload images and perform annotations

## 4. Data Management Workflow

### 4.1 Data Annotation
1. Annotate images in Label Studio
2. Export to YOLO format using the utility script:
```bash
./export_yolo.sh
```

### 4.2 Data Versioning with DVC
Our dataset repository: https://github.com/PP036/planes-dataset

#### Initial Setup
```bash
# Install DVC and initialize repository
pip install 'dvc[all]'
dvc init
mkdir -p dataset

# Configure MinIO as remote storage
dvc remote add -d storage s3://cars-dvc-storage
dvc remote modify storage endpointurl http://localhost:9000

# Set MinIO credentials
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
dvc remote modify storage --local access_key_id ${MINIO_ACCESS_KEY}
dvc remote modify storage --local secret_access_key ${MINIO_SECRET_KEY}

# Initial commit
git add .dvc .gitignore
git commit -m "Initialize DVC and configure storage"
```

#### Version Management Commands
```bash
# Track data changes
dvc add dataset
git add dataset.dvc .gitignore
git commit -m "Data version X"
dvc push

# Check data status and differences
dvc status
dvc diff

# Restore previous versions
git checkout <commit-hash>
dvc checkout

# Retrieve data in a fresh clone
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
dvc remote modify storage --local access_key_id ${MINIO_ACCESS_KEY}
dvc remote modify storage --local secret_access_key ${MINIO_SECRET_KEY}
dvc pull
```

## 5. Distributed Training

### 5.1 Ray Cluster Setup
```bash
# Start head node
ray start --head --port=6379 --dashboard-host=0.0.0.0

# Connect worker nodes (run on each worker)
ray start --address='<head-node-IP-address>:6379'
```
- Ray Dashboard: http://localhost:8265

### 5.2 Dataset Distribution
```bash
# Prepare dataset archive
tar -czvf dataset.tar.gz dataset/

# Copy to all nodes and extract
for NODE in node1 node2 node3; do
    scp dataset.tar.gz user@${NODE}:/path/to/working/directory/
    ssh user@${NODE} "cd /path/to/working/directory/ && tar -xzvf dataset.tar.gz"
done
```

### 5.3 Model Training
```bash
# Start distributed training
python train_yolo.py --data dataset/data.yaml --epochs 100 --batch-size 16 --distributed
```

### 5.4 Training Monitoring with W&B
```bash
# Setup W&B
pip install wandb
wandb login
```
- Dashboard access: https://wandb.ai/username/planes-detection
- Tracked metrics: loss, precision, recall, mAP
- Visualizations: prediction results, experiment configuration, model artifacts

# Setting up a Local Kubernetes Cluster

## Command Line Tools Installation
```shell script
# Install kubectl
brew install kubectl

# Install kind for local Kubernetes cluster
brew install kind

# Install kustomize for YAML configuration management
brew install kustomize

# Install helm for Kubernetes package management
brew install helm
```

## Docker Desktop Installation
Install Docker Desktop with at least 8GB of allocated memory.

## Recommended Tools
For convenient cluster interaction, you can install a visual tool: https://k8slens.dev/

## Deploying Local K8s and Ray Cluster

### Preparation
The week-3/k8s/ directory already contains all necessary configuration files:
- kind/kind-config.yaml - local Kubernetes cluster configuration
- ray-cluster-values.yaml - Ray cluster parameters for Helm
- setup_cluster.sh - automatic deployment script

### Cluster Deployment
```shell script
# Navigate to the configuration directory
cd k8s/

# Make the script executable
chmod +x setup_cluster.sh

# Run automatic deployment
./setup_cluster.sh
```

The script will:
- Create a Kind cluster
- Install KubeRay operator via Helm
- Deploy Ray cluster with configured parameters
- Set up port-forwarding for service access

### Verifying Cluster Operation
```shell script
# Check pod status
kubectl get pods

# Check Ray cluster status
kubectl exec $(kubectl get pod -l ray.io/node-type=head -o jsonpath='{.items[0].metadata.name}') -- ray status

# Open Ray Dashboard in browser
http://localhost:8265
```

### Available Services
After successful deployment, the following will be available:
- Ray Dashboard: http://localhost:8265 - web interface for cluster monitoring
- Ray Client: ray://localhost:10001 - endpoint for Python client connection
- Ray Serve: http://localhost:8000 - endpoint for model deployment

### Running a Test Task
```shell script
# Via Ray Jobs API
ray job submit --address http://localhost:8265 -- python -c "import ray; ray.init(); print(ray.cluster_resources())"

# Or via Python client
python -c "
import ray
ray.init('ray://localhost:10001')
print('Ray cluster resources:', ray.cluster_resources())
ray.shutdown()
"
```

### Training a Model on KubeRay Using CPU
```shell script
cd yolo-cpu
python submit_job.py
```

### Cluster Management
```shell script
# Stop port forwarding
pkill -f 'kubectl port-forward.*raycluster-kuberay-head-svc'

# Delete Ray cluster
helm uninstall raycluster
helm uninstall kuberay-operator

# Completely delete Kind cluster
kind delete cluster --name ray-cluster

# Restart cluster from scratch
kind delete cluster --name ray-cluster
./setup_cluster.sh
```

## 6. Сервінг моделей у Ray
### 6.1 Документація
- **Офіційна документація:** [https://docs.ray.io/en/latest/serve/configure-serve-deployment.html](https://docs.ray.io/en/latest/serve/configure-serve-deployment.html)

### 6.2 Локальне тестування
``` bash
# Запуск сервінгу моделі локально
serve run object_detection:entrypoint
```
### 6.3 Деплой на кластер
``` bash
# Запуск сервінгу на кластері
python run_serve.py

# Перевірка перенаправлення портів
ps aux | grep "kubectl port-forward"
```
### 6.4 Тестування API
``` bash
# Відправлення тестового запиту до API
python test.py
```
## CI/CD для доставки моделі

У цьому проєкті реалізовано повний цикл CI/CD з використанням **GitHub Actions**.

### 📦 Тренування моделі (CI)

- Запускається автоматично при `pull_request` в `main` або вручну.
- Відправляє задачу на кластер Ray для тренування моделі.
- Результати логуються в [Weights & Biases](https://wandb.ai/).

### 🚀 Деплой моделі (CD)

- Запускається вручну (`workflow_dispatch`).
- Виконує деплой нової версії моделі на **Ray Serve**, який доступний через інтерфейс HTTP.
- Для деплою використовується скрипт `week-4/ray-deploy/run_serve.py`.

### ⚙️ Інструкція по запуску

1. **Тренування**
   - GitHub Actions → Workflows → `Train on Ray Cluster` → `Run workflow`
2. **Деплой**
   - GitHub Actions → Workflows → `Deploy YOLOv8` → `Run workflow`

> Перед деплоєм переконайтесь, що кластер Ray активний і `run_serve.py` використовує останню модель з реєстру.

### 🔐 Секрети GitHub (використовуються у workflow)

- `WANDB_API_KEY`
- `WANDB_ENTITY`
- `WANDB_PROJECT

