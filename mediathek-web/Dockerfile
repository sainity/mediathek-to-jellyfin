FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -U yt-dlp

COPY app.py .

ENV URLS_FILE=/config/urls.txt
ENV FILME_URLS_FILE=/config/filme.txt
ENV FILME_DIR=/media/Filme

EXPOSE 5000

CMD ["python", "app.py"]
