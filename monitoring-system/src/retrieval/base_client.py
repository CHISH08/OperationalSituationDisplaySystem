from qdrant_client import QdrantClient
from qdrant_client.http import models

class BaseQdrantClient:
    def __init__(self, qdrant_host: str = "qdrant", qdrant_port: int = 6333,
                 collection_name: str = "geo_embeddings", vector_size: int = 512):
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._connect_collection()

    def _connect_collection(self):
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            if self.collection_name in collection_names:
                print(f"Подключено к коллекции '{self.collection_name}'")
            else:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
                print(f"Коллекция '{self.collection_name}' создана")
        except Exception as e:
            print(f"❌ Ошибка при подключении или создании коллекции: {str(e)}")

    def delete_collection(self) -> bool:
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"Коллекция '{self.collection_name}' успешно удалена")
            return True
        except Exception as e:
            print(f"❌ Ошибка удаления коллекции: {str(e)}")
            return False
