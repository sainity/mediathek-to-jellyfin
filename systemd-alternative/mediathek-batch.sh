#!/usr/bin/env bash
#
# mediathek-batch.sh — wird vom systemd-Timer aufgerufen.
# Liest Zeile für Zeile URLs (Sendungen, Kanäle, Playlists) aus
# ~/.config/mediathek-dl/urls.txt und lädt sie über mediathek-dl.sh.
#
# Leere Zeilen und Zeilen, die mit # beginnen, werden ignoriert.

set -euo pipefail

CONFIG_DIR="$HOME/.config/mediathek-dl"
URL_LIST="$CONFIG_DIR/urls.txt"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$CONFIG_DIR"

if [[ ! -f "$URL_LIST" ]]; then
    cat > "$URL_LIST" <<'EOF'
# Eine URL pro Zeile (Sendung, Serie, Kanal-Feed, ...)
# Zeilen mit # werden ignoriert.
# Beispiel:
# https://www.zdf.de/serien/beispiel-serie
EOF
    echo "Keine urls.txt gefunden, Vorlage angelegt unter: $URL_LIST"
    echo "Bitte URLs eintragen und den Timer erneut laufen lassen."
    exit 0
fi

while IFS= read -r url; do
    # Kommentare und leere Zeilen überspringen
    [[ -z "$url" || "$url" =~ ^[[:space:]]*# ]] && continue
    echo "== Lade: $url =="
    "$SCRIPT_DIR/mediathek-dl.sh" "$url" || echo "Warnung: Download fehlgeschlagen für $url" >&2
done < "$URL_LIST"
