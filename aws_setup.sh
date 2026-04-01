#!/bin/bash

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install PostgreSQL client
sudo apt install postgresql-client -y

# Install Redis server
sudo apt install redis-server -y

# Install Nginx
sudo apt install nginx -y

# Install certbot for SSL (optional)
sudo apt install certbot python3-certbot-nginx -y

# Create project directory
sudo mkdir -p /var/www/easybuy
sudo chown -R ubuntu:ubuntu /var/www/easybuy

# Install Python dependencies (run as ubuntu user)
cd /var/www/easybuy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt