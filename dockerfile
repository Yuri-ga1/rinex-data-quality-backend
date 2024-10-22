# Используйте официальный образ Python
FROM python:3.12

# Установка необходимых системных зависимостей (если необходимо)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Добавление Poetry в PATH
ENV PATH="/root/.local/bin:$PATH"

# Установка рабочей директории
WORKDIR /app

# Копирование файлов проекта в контейнер
COPY . .

# Установка зависимостей из pyproject.toml
RUN poetry install --no-root

# Команда для запуска вашего приложения
CMD ["poetry", "run", "python", "main.py"]
