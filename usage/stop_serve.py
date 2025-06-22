import ray
from ray import serve

ray.init(address="ray://localhost:10001")
serve.delete("yolo")   # Явное удаление приложения
serve.shutdown()       # Полный shutdown Serve
ray.shutdown()