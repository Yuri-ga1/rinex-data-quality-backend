#!/bin/bash

# Функция для установки Docker Compose
install_docker_compose() {
    echo "Installing Docker Compose..."

    # Скачиваем Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

    # Назначаем права на выполнение
    sudo chmod +x /usr/local/bin/docker-compose

    echo "Docker Compose installed successfully."
}

# Проверка наличия Docker Compose
if [[ $(which docker-compose) && $(docker-compose --version) ]]; then
    echo "Docker Compose not found."
    install_docker_compose
else
    echo "Docker Compose is already installed."
fi

echo "Running Docker Compose..."
sudo ufw allow 8000
sudo docker-compose up --build
