#!/usr/bin/env bash
#
# mediathek-check.sh — prüft alle URLs aus urls.txt auf neue Folgen,
# OHNE etwas herunterzuladen. Vergleicht dazu die aktuell verfügbaren
# Video-IDs (per --flat-playlist) mit dem Download-Archiv von
# mediathek-dl.sh. Nützlich, um vor dem eigentlichen Download zu sehen,
# was neu dazugekommen ist, oder um sich per Desktop-Benachrichtigung
# informieren zu lassen.
#
# Nutzung:
#   mediathek-check.sh            # Ausgabe auf der Konsole
#   mediathek-check.sh --notify   # zusätzlich Desktop-Benachrichtigung (notify-send)

set -euo pipefail

DOWNLOAD_DIR="${MEDIATHEK_DIR:-$HOME/Videos/Mediathek}"
ARCHIVE_FILE="$DOWNLOAD_DIR/.archive.txt"
CONFIG_DIR="$HOME/.config/mediathek-dl"
URL_LIST="$CONFIG_DIR/urls.txt"
NOTIFY=false

[[ "${1:-}" == "--notify" ]] && NOTIFY=true

mkdir -p "$DOWNLOAD_DIR" "$CONFIG_DIR"
touch "$ARCHIVE_FILE"

if [[ ! -f "$URL_LIST" ]]; then
    echo "Keine urls.txt gefunden unter: $URL_LIST" >&2
    echo "Erst mediathek-batch.sh einmal laufen lassen, um die Vorlage anzulegen." >&2
    exit 1
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
    echo "Fehler: yt-dlp ist nicht installiert oder nicht im PATH." >&2
    exit 1
fi

new_count=0
new_titles=()

while IFS= read -r url; do
    [[ -z "$url" || "$url" =~ ^[[:space:]]*# ]] && continue

    while IFS=$'\t' read -r extractor id title; do
        [[ -z "$id" ]] && continue
        extractor_lc="${extractor,,}"
        if ! grep -qxF "$extractor_lc $id" "$ARCHIVE_FILE"; then
            new_count=$((new_count + 1))
            new_titles+=("$title")
        fi
    done < <(yt-dlp --flat-playlist --no-warnings \
                --print "%(extractor_key)s	%(id)s	%(title)s" \
                "$url" 2>/dev/null || true)
done < "$URL_LIST"

if (( new_count > 0 )); then
    echo "$new_count neue Folge(n) gefunden:"
    printf ' - %s\n' "${new_titles[@]}"
    if $NOTIFY && command -v notify-send >/dev/null 2>&1; then
        notify-send "Mediathek" "$new_count neue Folge(n) verfügbar"
    fi
else
    echo "Keine neuen Folgen gefunden."
fi
