import torch
import open_clip
from PIL import Image

class RemoteCLIP:
    def __init__(self, model_name='ViT-B-32', ckpt_path=None, device='cuda'):
        """
        Инициализация модели RemoteCLIP.

        :param model_name: Название модели (например, 'ViT-B-32').
        :param ckpt_path: Путь к файлу с предобученными весами модели.
        :param device: Устройство для вычислений ('cpu' или 'cuda').
        """
        self.device = device

        # Загрузка модели и преобразований
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(model_name)
        self.tokenizer = open_clip.get_tokenizer(model_name)

        # Загрузка предобученных весов
        if ckpt_path:
            checkpoint = torch.load(ckpt_path, map_location='cpu')
            msg = self.model.load_state_dict(checkpoint, strict=False)
            print(f"Model state dict loaded with message: {msg}")

        self.model = self.model.to(self.device).eval()

    def encode_text(self, texts):
        """
        Создает эмбеддинги для текста.

        :param texts: Список текстовых строк.
        :return: Нормализованные эмбеддинги текста.
        """
        with torch.no_grad():
            text_tokens = self.tokenizer(texts).to(self.device)
            text_features = self.model.encode_text(text_tokens)
            text_features /= text_features.norm(dim=-1, keepdim=True)
        return text_features

    def encode_image(self, image_paths):
        """
        Создает эмбеддинги для изображений.

        :param image_paths: Список путей к изображениям.
        :return: Нормализованные эмбеддинги изображений.
        """
        images = [Image.open(path).convert("RGB") for path in image_paths]
        images_preprocessed = torch.stack([self.preprocess(image) for image in images]).to(self.device)

        with torch.no_grad():
            image_features = self.model.encode_image(images_preprocessed)
            image_features /= image_features.norm(dim=-1, keepdim=True)
        return image_features
