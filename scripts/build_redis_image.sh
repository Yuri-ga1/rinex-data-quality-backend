#!/bin/bash

echo "Building Redis Docker image..."
sudo docker build -t redis-image -f dockerfile.redis .

echo "Redis Docker image built successfully."
