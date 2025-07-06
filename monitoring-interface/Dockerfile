# Используем официальный Python образ на основе Alpine (легковесный)
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения и шаблоны
COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/

# Открываем порт, на котором работает приложение
EXPOSE 8333

# Запускаем приложение
CMD ["python", "app.py"]
