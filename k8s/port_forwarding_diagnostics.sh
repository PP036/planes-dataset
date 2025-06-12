bin/bash
set -e  # Останавливаться при ошибках
set -x  # Показывать выполняемые команды

echo "=== Диагностика и запуск порт-форвардинга ==="

# Убиваем существующие процессы порт-форвардинга
echo "Остановка существующих процессов порт-форвардинга..."
pkill -f "kubectl port-forward" || true

# Проверяем статус подов
echo "Проверка статуса подов..."
kubectl get pods --all-namespaces

# Настраиваем порт-форвардинг с выводом ошибок
echo "Настройка порт-форвардинга с выводом ошибок..."

# Ray Dashboard
kubectl port-forward service/raycluster-kuberay-head-svc 8265:8265 &
PID_RAY=$!
echo "Ray Dashboard PID: $PID_RAY"

# Prometheus
kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n prometheus-system 9090:9090 &
PID_PROM=$!
echo "Prometheus PID: $PID_PROM"

# Grafana
kubectl port-forward svc/prometheus-grafana -n prometheus-system 3000:80 &
PID_GRAFANA=$!
echo "Grafana PID: $PID_GRAFANA"

# Ждем запуска всех сервисов
echo "Ожидание запуска сервисов..."
sleep 10

# Проверяем, работают ли все процессы
echo "Проверка процессов порт-форвардинга..."
ps -p $PID_RAY > /dev/null && echo "✅ Ray Dashboard процесс активен" || echo "❌ Ray Dashboard процесс не активен"
ps -p $PID_PROM > /dev/null && echo "✅ Prometheus процесс активен" || echo "❌ Prometheus процесс не активен"
ps -p $PID_GRAFANA > /dev/null && echo "✅ Grafana процесс активен" || echo "❌ Grafana процесс не активен"

# Проверяем доступность сервисов
echo "Проверка доступности сервисов..."
curl -s --connect-timeout 5 http://localhost:8265 > /dev/null 2>&1 && echo "✅ Ray Dashboard доступен" || echo "❌ Ray Dashboard не доступен"
curl -s --connect-timeout 5 http://localhost:9090 > /dev/null 2>&1 && echo "✅ Prometheus доступен" || echo "❌ Prometheus не доступен"
curl -s --connect-timeout 5 http://localhost:3000 > /dev/null 2>&1 && echo "✅ Grafana доступен" || echo "❌ Grafana не доступен"

# Проверяем сетевые порты
echo "Проверка сетевых портов..."
netstat -tulpn | grep -E "8265|9090|3000"

echo "=== Диагностика завершена ==="