# Используем официальный образ Python
FROM python:3.9-slim-buster

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Gunicorn (для production)
RUN pip install gunicorn

# Задаем команду для запуска приложения (для production)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

# (Опционально) Команда для запуска в режиме разработки (для локального тестирования)
# CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
