#!/bin/zsh
# Запуск «Рабочего кабинета» локально
# Использование: ./run.sh  (или: zsh run.sh)
cd "$(dirname "$0")"
exec python3 -m streamlit run app.py --server.port 8501 --server.headless true
