import os
import uuid
from typing import List, Optional, Tuple, Union
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from PIL import Image
from qdrant_client.http import models

from .base_client import BaseQdrantClient
from .processing import ImageDataProcessor, ImageBatchProcessor, FolderScanner
import logging

# Логгер для ImageProcessor
logger = logging.getLogger(__name__)

class ImageQdrantIndexer(BaseQdrantClient):
    def __init__(self, embedder: any, cleaner: any,
                 qdrant_host: str = "qdrant", qdrant_port: int = 6333,
                 collection_name: str = "geo_embeddings", vector_size: int = 512):
        super().__init__(qdrant_host=qdrant_host, qdrant_port=qdrant_port,
                         collection_name=collection_name, vector_size=vector_size)
        self.embedder = embedder
        self.cleaner = cleaner
        self.batch_processor = ImageBatchProcessor(embedder)
        self.folder_scanner = FolderScanner(cleaner)

    def add_image_data(self, image_path: str, metadata: dict) -> None:
        """
        Обрабатывает одно изображение и загружает его в Qdrant.
        Используется для единичной загрузки.
        """
        data_processor = ImageDataProcessor(self.embedder)
        embedding, new_metadata = data_processor.process_single_image(image_path)
        metadata.update(new_metadata)
        file_name = os.path.basename(image_path)
        point_id = abs(hash(file_name)) % (10**18)
        self.client.upsert(
            collection_name=self.collection_name,
            points=[models.PointStruct(
                id=point_id,
                vector=embedding,
                payload=metadata,
            )]
        )

    def add_image_data_batch(self, image_paths: List[str]) -> None:
        """Обрабатывает батч изображений и загружает их в Qdrant."""
        points = self.batch_processor.process_batch(image_paths)
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

    def process_image_folder(
        self,
        folder_path: str,
        batch_size: int = 32,
        resize: int = 1024,
        show_progress: bool = True
    ) -> None:
        logger.info(f"[process_image_folder] Старт обработки: {folder_path}")
        images = self.folder_scanner.scan_folder(folder_path, resize=resize)
        total = len(images)
        if not images:
            logger.warning("[process_image_folder] Нет изображений для обработки")
            print("В указанной корневой папке нет изображений для обработки.")
            return

        logger.info(f"[process_image_folder] Всего изображений: {total}")

        progress = tqdm(
            total=total,
            desc="🔄 Обработка изображений",
            unit="img",
            disable=not show_progress
        )

        # Обрабатываем батчи один за другим
        num_batches = (total + batch_size - 1) // batch_size
        for batch_idx in range(num_batches):
            start = batch_idx * batch_size
            batch = images[start:start + batch_size]
            logger.info(f"[process_image_folder] Обработка батча #{batch_idx+1}/{num_batches}: {len(batch)} шт.")
            try:
                self.add_image_data_batch(batch)
                logger.info("[process_image_folder] Батч успешно обработан")
            except Exception as e:
                logger.error(f"[process_image_folder] Ошибка в батче #{batch_idx+1}: {e}", exc_info=True)
                print(f"\n🚨 Ошибка в батче #{batch_idx+1}: {e}")
            progress.update(len(batch))

        progress.close()
        logger.info("[process_image_folder] Обработка завершена")

    def search(self, query: Union[str, Image.Image], top_k: int = 5,
               coord_range: Optional[Tuple[float, float, float, float]] = None,
               start_datetime: Optional[str] = None, end_datetime: Optional[str] = None) -> List[dict]:
        """
        Выполняет поиск по тексту или изображению с дополнительной фильтрацией по координатам и времени.
        """
        if isinstance(query, str):
            embedding = self.embedder.encode_text([query]).cpu().numpy()[0]
        else:
            embedding = self.embedder.encode_image([query]).cpu().numpy()[0]

        must_conditions = []
        if coord_range:
            min_lat, max_lat, min_lon, max_lon = coord_range
            must_conditions.extend([
                models.FieldCondition(
                    key="lat",
                    range=models.Range(gte=min_lat, lte=max_lat)
                ),
                models.FieldCondition(
                    key="lon",
                    range=models.Range(gte=min_lon, lte=max_lon)
                )
            ])
        if start_datetime and start_datetime.strip():
            try:
                if "T" not in start_datetime:
                    start_datetime += "T00:00:00"
                start_ts = datetime.fromisoformat(start_datetime).timestamp()
                must_conditions.append(models.FieldCondition(
                    key="timestamp", range=models.Range(gte=start_ts)
                ))
            except Exception as e:
                print(f"Ошибка преобразования start_datetime: {e}")
        if end_datetime and end_datetime.strip():
            try:
                if "T" not in end_datetime:
                    end_datetime += "T23:59:59"
                end_ts = datetime.fromisoformat(end_datetime).timestamp()
                must_conditions.append(models.FieldCondition(
                    key="timestamp", range=models.Range(lte=end_ts)
                ))
            except Exception as e:
                print(f"Ошибка преобразования end_datetime: {e}")
        filter_ = models.Filter(must=must_conditions) if must_conditions else None
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding.tolist(),
            query_filter=filter_,
            limit=top_k,
        )
        return [{
            "id": hit.id,
            "score": hit.score,
            "payload": {**hit.payload, "coordinates": (hit.payload.get("lat"), hit.payload.get("lon"))}
        } for hit in results]
