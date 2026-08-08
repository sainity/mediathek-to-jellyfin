#!/usr/bin/env bash
#
# mediathek-dl.sh — yt-dlp Wrapper für ARD/ZDF/arte/3sat & Co.
# Lädt immer die beste verfügbare Video-/Audioqualität, merged nach mp4,
# bettet Untertitel/Thumbnail/Metadaten ein und führt ein Download-Archiv,
# damit nichts doppelt geladen wird.
#
# Nutzung:
#   mediathek-dl.sh <URL> [<URL2> ...]
#   mediathek-dl.sh -a pfad/zu/liste.txt      # Batch-Datei mit einer URL pro Zeile
#
# Zielordner per Umgebungsvariable änderbar:
#   MEDIATHEK_DIR=/pfad mediathek-dl.sh <URL>

set -euo pipefail

DOWNLOAD_DIR="${MEDIATHEK_DIR:-$HOME/Videos/Mediathek}"
ARCHIVE_FILE="$DOWNLOAD_DIR/.archive.txt"

mkdir -p "$DOWNLOAD_DIR"

if ! command -v yt-dlp >/dev/null 2>&1; then
    echo "Fehler: yt-dlp ist nicht installiert oder nicht im PATH." >&2
    exit 1
fi

yt-dlp \
    -f "bestvideo*+bestaudio/best" \
    --merge-output-format mp4 \
    --restrict-filenames \
    --no-overwrites \
    --download-archive "$ARCHIVE_FILE" \
    --embed-subs --sub-langs "de.*,deu" --write-subs \
    --embed-metadata \
    --embed-thumbnail \
    --convert-thumbnails jpg \
    --concurrent-fragments 4 \
    -o "$DOWNLOAD_DIR/Shows/%(series,playlist_title,uploader,extractor_key)s/%(series,playlist_title,uploader,extractor_key)s - %(upload_date>%Y-%m-%d)s - %(title)s [%(id)s].%(ext)s" \
    "$@"
