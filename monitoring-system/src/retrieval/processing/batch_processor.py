import os
import uuid
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from qdrant_client.http import models

from ..utils import ImageMetadataExtractor, S3ImageHandler


class ImageBatchProcessor(ImageMetadataExtractor, S3ImageHandler):
    def __init__(self, embedder: any):
        self.embedder = embedder

    def process_batch(self, image_paths: List[str]) -> List[models.PointStruct]:
        """
        Обрабатывает батч изображений: скачивает файлы из S3, вычисляет эмбеддинги пакетно и формирует объекты Qdrant.
        """
        new_paths = []       # Пути для обработки (локальные или исходные)
        downloaded_files = []  # Скачанные локальные файлы (для последующей очистки)
        original_paths = []    # Исходные пути для метаданных

        s3_paths = [p for p in image_paths if p.startswith("s3://")]
        downloaded_mapping = {}
        if s3_paths:
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_to_s3 = {executor.submit(self.get_local_image_path, s3): s3 for s3 in s3_paths}
                for future in as_completed(future_to_s3):
                    s3_path = future_to_s3[future]
                    try:
                        local_path = future.result()
                        downloaded_mapping[s3_path] = local_path
                    except Exception as e:
                        print(f"Ошибка загрузки {s3_path}: {e}")

        for path in image_paths:
            original_paths.append(path)
            if path.startswith("s3://"):
                if path in downloaded_mapping:
                    local_path = downloaded_mapping[path]
                    new_paths.append(local_path)
                    downloaded_files.append(local_path)
                else:
                    new_paths.append(path)
            else:
                new_paths.append(path)

        embeddings = self.embedder.encode_image(new_paths).cpu().numpy()
        points = []
        for idx, local_path in enumerate(new_paths):
            point_id = str(uuid.uuid4())
            metadata = {"source": original_paths[idx]}

            geo_data = self.extract_gps_coordinates(local_path)
            if geo_data:
                metadata.update({"lat": float(geo_data[0]), "lon": float(geo_data[1])})

            dt = self.extract_datetime(local_path)
            if dt:
                metadata.update({
                    "timestamp": dt.timestamp(),
                    "date": [dt.year, dt.month, dt.day],
                    "time": [dt.hour, dt.minute, dt.second]
                })

            points.append(models.PointStruct(
                id=point_id,
                vector=embeddings[idx].tolist(),
                payload=metadata
            ))

        for f in downloaded_files:
            if os.path.exists(f):
                os.remove(f)

        return points
