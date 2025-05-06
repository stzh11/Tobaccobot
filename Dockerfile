# syntax=docker/dockerfile:1
FROM python:3.12-slim

# 1. ставим зависимости
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. копируем весь проект
COPY . .

# 3. запускаем веб-сервер
CMD ["python", "webhook.py"]
