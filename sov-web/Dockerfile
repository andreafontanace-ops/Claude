FROM python:3.13-slim
WORKDIR /app
COPY amazon-sov /app/amazon-sov
COPY sov-web /app/sov-web
RUN pip install --no-cache-dir /app/amazon-sov "/app/sov-web[postgres]"
WORKDIR /app/sov-web
ENV SOV_ENV=production
EXPOSE 8000
# il comando cambia tra sito (web) e raccolte (worker): vedi docker-compose.yml
CMD ["uvicorn", "sovweb.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
