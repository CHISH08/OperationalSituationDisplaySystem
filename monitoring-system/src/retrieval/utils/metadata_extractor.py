import exifread
from datetime import datetime
from typing import Optional, Tuple

class ImageMetadataExtractor:
    @staticmethod
    def extract_gps_coordinates(image_path: str) -> Optional[Tuple[float, float]]:
        """Извлекает широту и долготу из EXIF-данных изображения."""
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        if not tags:
            return None
        gps_latitude = tags.get('GPS GPSLatitude')
        gps_latitude_ref = tags.get('GPS GPSLatitudeRef')
        gps_longitude = tags.get('GPS GPSLongitude')
        gps_longitude_ref = tags.get('GPS GPSLongitudeRef')
        if not all([gps_latitude, gps_latitude_ref, gps_longitude, gps_longitude_ref]):
            return None

        def convert_to_decimal(gps_value, ref):
            degrees = gps_value.values[0].num / gps_value.values[0].den
            minutes = gps_value.values[1].num / gps_value.values[1].den
            seconds = gps_value.values[2].num / gps_value.values[2].den
            decimal = degrees + (minutes / 60) + (seconds / 3600)
            if ref.values in ['S', 'W']:
                decimal = -decimal
            return decimal

        lat = convert_to_decimal(gps_latitude, gps_latitude_ref)
        lon = convert_to_decimal(gps_longitude, gps_longitude_ref)
        return (lat, lon)

    @staticmethod
    def extract_datetime(image_path: str) -> Optional[datetime]:
        """Извлекает дату и время съемки из EXIF-данных изображения."""
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        dt_tag = tags.get('EXIF DateTimeOriginal') or tags.get('Image DateTime')
        if not dt_tag:
            return None
        try:
            dt = datetime.strptime(str(dt_tag), "%Y:%m:%d %H:%M:%S")
            return dt
        except Exception as e:
            print(f"Ошибка преобразования даты для {image_path}: {e}")
            return None
