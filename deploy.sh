#!/bin/bash

cd /home/ubuntu/ProjectPAD66

# Atualiza o código
git pull origin main

# Ativa o venv
source venv/bin/activate

# Mata processos antigos
pkill -f app.py
pkill -f worker.py
sleep 2

# Sobe de novo com nohup
nohup python3 app.py > flask.log 2>&1 &
nohup python3 worker.py > worker.log 2>&1 &
