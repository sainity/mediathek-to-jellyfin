FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -U yt-dlp

# Supercronic: leichtgewichtiger Cron-Ersatz für Container, ohne systemd-Abhängigkeit
# (das reguläre "cron"-Paket zieht auf neueren Debian-Basisimages systemd als
# Abhängigkeit mit rein, dessen Postinstall-Skript im Docker-Build scheitert)
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.48/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=016b7c9aebfc8d9fd9526e8ba33b191fc524485f

RUN curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" /usr/local/bin/supercronic

COPY mediathek-dl.sh mediathek-batch.sh mediathek-check.sh mediathek-film-dl.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/mediathek-dl.sh \
             /usr/local/bin/mediathek-batch.sh \
             /usr/local/bin/mediathek-check.sh \
             /usr/local/bin/mediathek-film-dl.sh

COPY crontab /etc/crontab

# Eigenes Home-Verzeichnis, das dem später verwendeten Container-User (UID 1000)
# gehört -- /root ist für nicht-root-User nicht beschreibbar.
RUN mkdir -p /home/mediathek && chown -R 1000:100 /home/mediathek
ENV HOME=/home/mediathek

# Supercronic übernimmt automatisch alle ENV-Variablen des Containers
# (z.B. MEDIATHEK_DIR aus der docker-compose.yml) für die Cron-Jobs
CMD ["supercronic", "/etc/crontab"]
