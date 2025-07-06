import os
import cv2
import numpy as np
from shapely.geometry import Polygon
from matching import get_matcher

class ImageFolderCleaner:
    """
    Класс для фильтрации изображений в папке на основе процентного пересечения.

    Аргументы:
      model_name (str): Название модели для мэтчинга (например, "superpoint-lg").
      deletion_threshold (float): Порог удаления (в процентах пересечения).
      device (str, optional): Устройство для вычислений (например, "cuda").
    """
    def __init__(self, model_name: str = "superpoint-lg", deletion_threshold: int = 40, device: str = "cuda"):
        self.deletion_threshold = deletion_threshold
        self.matcher = get_matcher([model_name], device=device)

    def compute_image_overlap(self, image_path1: str, image_path2: str, resize: int = 1024) -> float:
        """
        Загружает два изображения, вычисляет матрицу гомографии и определяет процент площади первого изображения,
        который пересекается со вторым.

        Параметры:
          image_path1 (str): Путь к первому изображению.
          image_path2 (str): Путь ко второму изображению.
          resize (int, optional): Размер для масштабирования изображения (по меньшей стороне).

        Возвращает:
          overlap_percentage (float): Процент площади первого изображения, пересекающейся со вторым.
        """
        # Загрузка изображений через matcher.image_loader
        img1 = self.matcher.image_loader(image_path1, resize=resize)
        img2 = self.matcher.image_loader(image_path2, resize=resize)

        def get_image_shape(img):
            if hasattr(img, 'shape'):
                # Если изображение в формате (C, H, W)
                if len(img.shape) == 3:
                    if img.shape[0] == 3:
                        return (img.shape[1], img.shape[2])
                    else:
                        return img.shape[:2]
                elif len(img.shape) == 2:
                    return img.shape
                else:
                    raise ValueError("Неверная форма изображения")
            else:
                raise ValueError("Изображение не имеет атрибута shape")

        shape1 = get_image_shape(img1)
        shape2 = get_image_shape(img2)
        h1, w1 = shape1
        h2, w2 = shape2

        # Вычисляем гомографию между изображениями с помощью matcher
        result = self.matcher(img1, img2)
        H = result["H"]

        # Преобразуем H в numpy-массив типа float32
        H = np.array(H, dtype=np.float32)

        if H.shape != (3, 3):
            raise ValueError("Матрица гомографии имеет некорректную форму: {}".format(H.shape))

        # Определяем углы первого изображения
        pts1 = np.array([[0, 0], [w1, 0], [w1, h1], [0, h1]], dtype=np.float32).reshape(-1, 1, 2)
        pts1_transformed = cv2.perspectiveTransform(pts1, H).reshape(-1, 2)

        poly1 = Polygon(pts1_transformed)
        pts2 = np.array([[0, 0], [w2, 0], [w2, h2], [0, h2]], dtype=np.float32)
        poly2 = Polygon(pts2)

        # Вычисляем площадь пересечения многоугольников
        intersection = poly1.intersection(poly2)
        overlap_area = intersection.area if not intersection.is_empty else 0.0
        img1_area = poly1.area

        overlap_percentage = (overlap_area / img1_area) * 100 if img1_area > 0 else 0.0

        return overlap_percentage

    def process_folder(self, folder_path: str, resize: int = 1024) -> list:
        """
        Проходит по изображениям в указанной папке и возвращает список путей, 
        удовлетворяющих условию: текущее изображение добавляется, если его процент пересечения
        с предыдущим (базовым) изображением меньше или равен заданному порогу.

        Алгоритм:
          - Первое изображение всегда сохраняется.
          - Для каждого следующего изображения вычисляется процент пересечения с текущим базовым.
          - Если пересечение больше порога, изображение пропускается.
          - Если пересечение меньше или равно порога, изображение сохраняется и становится новым базовым.
          - При возникновении ошибок (например, TopologyException или неверная матрица гомографии) 
            ошибка логируется, а процент пересечения считается равным 0.

        Параметры:
          folder_path (str): Путь к папке с изображениями.
          resize (int, optional): Размер для масштабирования изображения при вычислении пересечения.

        Возвращает:
          list: Список путей к изображениям, которые остались.
        """
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
        files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(valid_extensions)])

        if not files:
            print("В указанной папке нет изображений.")
            return []

        file_paths = [os.path.join(folder_path, f) for f in files]
        kept_images = [file_paths[0]]
        current_image = file_paths[0]
        print(f"Базовое изображение: {current_image}")

        for next_image in file_paths[1:]:
            try:
                overlap = self.compute_image_overlap(current_image, next_image, resize=resize)
                print(f"Пересечение между '{current_image}' и '{next_image}' = {overlap:.2f}%")
            except Exception as e:
                print(f"Ошибка при обработке '{current_image}' и '{next_image}': {e}")
                overlap = 0.0  # При ошибке считаем пересечение равным 0

            if overlap > self.deletion_threshold:
                print(f"Изображение '{next_image}' пропущено (пересечение > порога)")
            else:
                kept_images.append(next_image)
                current_image = next_image
                print(f"Новое базовое изображение: {current_image}")

        return kept_images
