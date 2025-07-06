# Базовый runtime-образ с PyTorch 2.7.0 + CUDA 12.6 + cuDNN 9
FROM pytorch/pytorch:2.7.0-cuda12.6-cudnn9-runtime

# Отключаем интерактивный режим для apt
ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем системные зависимости и инструменты сборки
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        libgl1-mesa-glx \
        libglib2.0-0 \
        build-essential \
        cmake && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем Python-зависимости проекта
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Устанавливаем torch-cluster из PyG-колес
RUN pip install --no-cache-dir \
      torch-cluster \
      -f https://data.pyg.org/whl/torch-2.7.0+cu126.html

# =========================
# Сборка image-matching-models
# =========================
# Клонируем репозиторий и устанавливаем
WORKDIR /opt
RUN git clone --recursive https://github.com/alexstoken/image-matching-models && \
    cd image-matching-models && \
    pip install '.[all]'

# =========================
# Возврат в рабочую директорию и копирование основного кода
# =========================
WORKDIR /app
COPY . /app

# Пробрасываем порт uvicorn
EXPOSE 8000

# Запуск FastAPI приложения через uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
