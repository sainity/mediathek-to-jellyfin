#!/usr/bin/env bash
#
# mediathek-film-dl.sh — wie mediathek-dl.sh, aber für EINZELNE Filme/Dokus
# aus der Mediathek statt für Serien. Legt die Datei im Jellyfin-Filme-Schema
# "Titel (Jahr)/Titel (Jahr) [id].ext" ab, damit TheMovieDb sie korrekt matcht.
#
# Nutzung:
#   mediathek-film-dl.sh <URL> [<URL2> ...]
#
# Zielordner per Umgebungsvariable änderbar:
#   FILME_DIR=/pfad mediathek-film-dl.sh <URL>

set -euo pipefail

FILME_DIR="${FILME_DIR:-/media/Filme}"
ARCHIVE_FILE="$FILME_DIR/.archive.txt"

mkdir -p "$FILME_DIR"

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
    -o "$FILME_DIR/%(title)s (%(release_year,upload_date>%Y)s)/%(title)s (%(release_year,upload_date>%Y)s) [%(id)s].%(ext)s" \
    "$@"
