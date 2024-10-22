# Функция для установки Docker
install_docker() {
    echo "Installing Docker..."
    
    # Обновление списка пакетов
    sudo apt-get update
    
    # Установка необходимых пакетов
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        software-properties-common

    # Добавление GPG-ключа Docker
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

    # Добавление репозитория Docker
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

    # Обновление списка пакетов снова
    sudo apt-get update

    # Установка Docker
    sudo apt-get install -y docker-ce

    # Запуск Docker
    sudo systemctl start docker
    sudo systemctl enable docker

    echo "Docker installed successfully."
}

# Проверка наличия Docker
check_docker(){
    if [[ $(which docker) && $(docker --version) ]]; then
        echo "Docker not found."
        install_docker
    else
        echo "Docker is already installed."
    fi
}