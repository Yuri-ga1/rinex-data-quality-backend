#!/bin/bash

. ./scripts/install_docker.sh

check_docker

# Сборка Docker образа
echo "Building Docker image..."
sudo docker build -t rinex-data-quality-backend .
