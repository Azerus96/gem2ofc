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
# Используем gevent worker и 1 worker для начала.  Можно изменить при необходимости.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--worker-class", "gevent", "app:app"]


# (Опционально) Команда для запуска в режиме разработки (для локального тестирования)
# Раскомментируйте следующую строку и закомментируйте строку с gunicorn, если хотите использовать
# встроенный сервер Flask для разработки.
# CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
