import ray
from ray import serve

ray.init(address="ray://localhost:10001")

# Видаляємо застосунок за назвою
serve.delete("yolo")

print("Serve application 'yolo' stopped.")

ray.shutdown()