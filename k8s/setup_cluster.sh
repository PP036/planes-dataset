#!/bin/bash

# Обробка помилок і вихід при першій помилці
set -e

# Додаємо функцію для обробки переривання
cleanup() {
  echo "Очищення ресурсів..."
  pkill -f "kubectl port-forward" || true
}

# Встановлюємо обробник сигналів
trap cleanup EXIT INT TERM

# Визначення змінних
PROMETHEUS_NAMESPACE="prometheus-system"
RAY_CLUSTER_NAME="raycluster"
GRAFANA_USER="admin"
GRAFANA_PASSWORD="prom-operator"
MAX_WAIT_TIME=300  # 5 хвилин таймаут за замовчуванням

# Перевірка необхідних інструментів
echo "Перевірка необхідних інструментів..."
for cmd in kind kubectl helm jq curl; do
  if ! command -v $cmd &> /dev/null; then
    echo "❌ Помилка: команда '$cmd' не знайдена. Будь ласка, встановіть її."
    exit 1
  fi
done

# Перевірка наявності необхідних файлів
echo "Перевірка наявності необхідних файлів..."
for file in kind/kind-config.yaml ray-cluster/ray-cluster-values.yaml monitoring/prometheus/prometheus-values.yaml monitoring/prometheus/ray-servicemonitor.yaml monitoring/prometheus/ray-podmonitor.yaml monitoring/prometheus/ray-prometheus-rules.yaml; do
  if [ ! -f "$file" ]; then
    echo "❌ Помилка: файл $file не знайдено"
    exit 1
  fi
done

echo "=== 0. Cleaning up any existing cluster ==="
# Зупиняємо будь-які існуючі перенаправлення портів
pkill -f "kubectl port-forward.*raycluster-kuberay-head-svc" || true
pkill -f "kubectl port-forward.*prometheus" || true
pkill -f "kubectl port-forward.*grafana" || true

# Видаляємо існуючий кластер, якщо він є
kind delete cluster --name ray-cluster || true

echo "=== 1. Starting Kind cluster ==="
mkdir -p /tmp/kubeflow-data
if ! kind create cluster --config kind/kind-config.yaml; then
  echo "❌ Помилка при створенні кластера Kind"
  exit 1
fi

# Очікуємо готовності кластера
echo "Waiting for cluster to be ready..."
if ! kubectl wait --for=condition=ready nodes --all --timeout=${MAX_WAIT_TIME}s; then
  echo "❌ Помилка: кластер не став готовим за ${MAX_WAIT_TIME} секунд"
  exit 1
fi

echo "=== 2. Installing Prometheus Stack ==="
# https://docs.ray.io/en/latest/cluster/kubernetes/k8s-ecosystem/prometheus-grafana.html
# Додаємо Helm репозиторії
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update

# Створюємо namespace для prometheus
kubectl create namespace ${PROMETHEUS_NAMESPACE} || true

# Встановлюємо kube-prometheus-stack
echo "Installing kube-prometheus-stack..."
if ! helm install prometheus prometheus-community/kube-prometheus-stack \
    --namespace ${PROMETHEUS_NAMESPACE} \
    --version 61.7.2 \
    -f monitoring/prometheus/prometheus-values.yaml; then
  echo "❌ Помилка при встановленні Prometheus Stack"
  exit 1
fi

echo "=== 3. Waiting for Prometheus stack to be ready ==="
echo "Waiting for Prometheus operator..."
if ! kubectl wait --for=condition=available --timeout=${MAX_WAIT_TIME}s deployment/prometheus-kube-prometheus-operator -n ${PROMETHEUS_NAMESPACE}; then
  echo "❌ Помилка: оператор Prometheus не став доступним за ${MAX_WAIT_TIME} секунд"
  exit 1
fi

echo "Waiting for Prometheus StatefulSet to be created..."
start_time=$(date +%s)
timeout_reached=false

while true; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))

    if [ $elapsed -gt $MAX_WAIT_TIME ]; then
        echo "❌ Таймаут: Prometheus StatefulSet не був створений за ${MAX_WAIT_TIME} секунд"
        timeout_reached=true
        break
    fi

    if kubectl get statefulset prometheus-prometheus-kube-prometheus-prometheus -n ${PROMETHEUS_NAMESPACE} >/dev/null 2>&1; then
        echo "✅ Prometheus StatefulSet found"
        break
    fi
    echo "⏳ Prometheus StatefulSet not found yet, waiting... ($elapsed сек із ${MAX_WAIT_TIME})"
    sleep 10
done

if [ "$timeout_reached" = true ]; then
    echo "Пропускаємо очікування Prometheus StatefulSet, продовжуємо далі..."
else
    echo "Waiting for Prometheus pod to be ready..."
    if ! kubectl wait --for=condition=ready --timeout=${MAX_WAIT_TIME}s pod -l app.kubernetes.io/name=prometheus -n ${PROMETHEUS_NAMESPACE}; then
        echo "❌ Помилка: под Prometheus не став готовим за ${MAX_WAIT_TIME} секунд"
        echo "⚠️ Продовжуємо виконання скрипту..."
    else
        echo "✅ Prometheus pod is ready"
    fi
fi

echo "Waiting for Grafana pod to be ready..."
if ! kubectl wait --for=condition=ready --timeout=${MAX_WAIT_TIME}s pod -l app.kubernetes.io/name=grafana -n ${PROMETHEUS_NAMESPACE}; then
    echo "❌ Помилка: под Grafana не став готовим за ${MAX_WAIT_TIME} секунд"
    echo "⚠️ Продовжуємо виконання скрипту..."
else
    echo "✅ Grafana pod is ready"
fi

echo "=== 4. Installing Ray Operator ==="
helm install kuberay-operator kuberay/kuberay-operator

echo "Waiting for KubeRay operator to be ready..."
if ! kubectl wait --for=condition=available --timeout=${MAX_WAIT_TIME}s deployment/kuberay-operator; then
    echo "❌ Помилка: оператор KubeRay не став доступним за ${MAX_WAIT_TIME} секунд"
    exit 1
fi

echo "=== 5. Installing Ray Cluster ==="
if ! helm install ${RAY_CLUSTER_NAME} kuberay/ray-cluster \
    -f ray-cluster/ray-cluster-values.yaml; then
    echo "❌ Помилка при встановленні кластера Ray"
    exit 1
fi

# Виводимо інформацію про встановлений кластер для діагностики
helm status ${RAY_CLUSTER_NAME}

echo "=== 6. Configuring Prometheus monitoring for Ray ==="
echo "Setting up ServiceMonitor for Ray..."
kubectl apply -f monitoring/prometheus/ray-servicemonitor.yaml

echo "Setting up PodMonitor for Ray..."
kubectl apply -f monitoring/prometheus/ray-podmonitor.yaml

echo "Setting up Prometheus Rules for Ray..."
kubectl apply -f monitoring/prometheus/ray-prometheus-rules.yaml

echo "=== 7. Waiting for Ray pods to be created ==="
echo "Waiting for Ray head pod to be created (це може зайняти деякий час)..."

# Даємо час на запуск подів
sleep 45

# Виводимо інформацію про поди для діагностики
echo "Поточні поди в кластері:"
kubectl get pods --all-namespaces | grep -E 'ray|kuberay|raycluster'

# Визначаємо сервіс для Ray dashboard
RAY_SERVICE=$(kubectl get svc -l ray.io/node-type=head -o name 2>/dev/null ||
              kubectl get svc | grep -E 'raycluster.*head' | awk '{print $1}' | head -n1)

echo "Ray service: $RAY_SERVICE"

# Намагаємось знайти pod head-ноди з урахуванням нашої конфігурації
echo "Пошук Ray head pod..."

# Підхід 1: Пошук за міткою ray.io/node-type=head
HEAD_POD=$(kubectl get pods -l ray.io/node-type=head -o name 2>/dev/null | sed 's|pod/||')

# Підхід 2: Пошук за іменем, якщо перший підхід не спрацював
if [ -z "$HEAD_POD" ]; then
    HEAD_POD=$(kubectl get pods | grep -E "${RAY_CLUSTER_NAME}.*kuberay-head" | awk '{print $1}' | head -n1)
fi

# Підхід 3: Пошук усіх подів, що містять "ray" та "head"
if [ -z "$HEAD_POD" ]; then
    HEAD_POD=$(kubectl get pods | grep -E ".*ray.*head.*" | awk '{print $1}' | head -n1)
fi

# Якщо всі підходи не спрацювали, виводимо повідомлення про помилку з повною діагностикою
if [ -z "$HEAD_POD" ]; then
    echo "❌ Помилка: не знайдено head pod для Ray кластера"
    echo "Усі поди в кластері:"
    kubectl get pods --all-namespaces
    echo "Усі сервіси в кластері:"
    kubectl get svc --all-namespaces
    echo "Очищення ресурсів..."
    exit 1
fi

echo "Знайдено Ray head pod: $HEAD_POD"

echo "=== 9. Waiting for Ray cluster to be ready ==="
echo "Waiting for Ray head pod to be ready..."
if ! kubectl wait --for=condition=ready --timeout=${MAX_WAIT_TIME}s pod/$HEAD_POD; then
    echo "❌ Помилка: Ray head pod не став готовим за ${MAX_WAIT_TIME} секунд"
    echo "⚠️ Продовжуємо виконання скрипту..."
else
    echo "✅ Ray head pod is ready"
fi

echo "=== 10. Verifying cluster health ==="
echo "Checking cluster status..."
kubectl get pods -l ray.io/cluster=${RAY_CLUSTER_NAME} -o wide || echo "⚠️ Ray pods may not be labeled as expected, trying alternative methods..."
kubectl get pods | grep -E "${RAY_CLUSTER_NAME}|ray|kuberay" || echo "⚠️ No Ray pods found with simple grep search"

echo "Checking Ray status..."
echo "Запуск 'ray status' всередині поду $HEAD_POD..."
RAY_STATUS=$(kubectl exec $HEAD_POD -c ray-head -- ray status 2>/dev/null || echo "Ray status failed")
echo "$RAY_STATUS"

echo "=== 8. Starting port-forwards for services ==="
echo "Setting up Prometheus port-forward..."
kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n ${PROMETHEUS_NAMESPACE} 9090:9090 &
echo "Prometheus доступний за адресою: http://localhost:9090"

echo "Setting up Grafana port-forward..."
kubectl port-forward svc/prometheus-grafana -n ${PROMETHEUS_NAMESPACE} 3000:80 &
echo "Grafana доступна за адресою: http://localhost:3000"

echo "Setting up Ray Dashboard port-forward..."
kubectl port-forward pod/$HEAD_POD 8265:8265 &
echo "Ray Dashboard доступний за адресою: http://localhost:8265"

echo "Setting up Ray Client API port-forward..."
kubectl port-forward pod/$HEAD_POD 10001:10001 &
echo "Ray Client API доступний за адресою: ray://localhost:10001"

echo "=== 12. Importing local dashboards from k8s/monitoring/grafana ==="

# Даємо Grafana кілька секунд для повного запуску
sleep 5

for dashboard in monitoring/grafana/*.json; do
    NAME=$(basename "$dashboard" .json)
    echo "📊 Importing $NAME..."

    jq -n \
      --slurpfile dash "$dashboard" \
      --arg msg "Imported from local file: $NAME.json" \
      '{dashboard: $dash[0], overwrite: true, message: $msg}' > /tmp/dashboard_payload.json

    RESPONSE=$(curl -s -X POST http://localhost:3000/api/dashboards/db \
      -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
      -H "Content-Type: application/json" \
      --data-binary @/tmp/dashboard_payload.json)

    echo "$NAME → $(echo "$RESPONSE" | jq -r '.status // .message // .error // "❌ Failed"')"
done

echo "=== 11. Setup complete! ==="
echo "Ray Dashboard: http://localhost:8265"
echo "Ray Client API: ray://localhost:10001"
echo "Prometheus: http://localhost:9090"
echo "Grafana: http://localhost:3000 (user: $GRAFANA_USER, password: $GRAFANA_PASSWORD)"

echo ""
echo "🔄 Щоб зупинити перенаправлення портів, натисніть Ctrl+C"
echo "❗ При зупинці буде виконано очищення ресурсів"

wait