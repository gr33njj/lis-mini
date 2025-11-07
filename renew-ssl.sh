#!/bin/bash
# Автообновление SSL сертификата

# Остановить Nginx
systemctl stop nginx
docker compose -f /opt/lis-md/docker-compose.yml stop nginx

# Обновить сертификат
certbot renew --quiet

# Запустить Nginx
docker compose -f /opt/lis-md/docker-compose.yml start nginx
systemctl start nginx

# Перезапустить для применения
docker compose -f /opt/lis-md/docker-compose.yml restart nginx
