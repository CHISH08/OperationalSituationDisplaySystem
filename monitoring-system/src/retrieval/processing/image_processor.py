import os
import uuid
from typing import Tuple, Optional
from ..utils import ImageMetadataExtractor, S3ImageHandler

class ImageDataProcessor(ImageMetadataExtractor, S3ImageHandler):
    def __init__(self, embedder: any):
        self.embedder = embedder

    def process_single_image(self, image_path: str, source: Optional[str] = None) -> Tuple[list, dict]:
        """
        Обрабатывает одно изображение, возвращая эмбеддинг и собранные метаданные.
        """
        local_path = self.get_local_image_path(image_path)
        metadata = {}
        if source:
            metadata["source"] = source

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

        embedding = self.embedder.encode_image([local_path]).cpu().numpy()[0]

        # Если файл скачан из S3 – удаляем временный файл
        if image_path.startswith("s3://") and os.path.exists(local_path):
            os.remove(local_path)
        return embedding.tolist(), metadata
