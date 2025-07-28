#!/bin/bash

echo "🚀 Iniciando deploy do PAD66..."

cd /home/ubuntu/ProjectPAD66 || exit 1

echo "📥 Puxando alterações do GitHub..."
git pull origin main

echo "🔁 Reiniciando processo no PM2..."
pm2 restart pad66

echo "✅ Deploy finalizado com sucesso!"
pm2 status pad66
