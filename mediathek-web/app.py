import os
import re
import subprocess
import threading
from datetime import datetime

from flask import Flask, request, redirect, url_for, render_template_string, jsonify

app = Flask(__name__)

URLS_FILE = os.environ.get("URLS_FILE", "/config/urls.txt")
FILME_URLS_FILE = os.environ.get("FILME_URLS_FILE", "/config/filme.txt")
FILME_DIR = os.environ.get("FILME_DIR", "/media/Filme")

# In-memory Status der Film-Downloads (geht bei Container-Neustart verloren,
# das ist fuer diesen Zweck okay -- die Datei mit den URLs bleibt erhalten)
film_jobs = {}
film_jobs_lock = threading.Lock()

TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mediathek-URLs verwalten</title>
<style>
    :root {
        --bg: #0f1115;
        --card: #171a21;
        --border: #2a2e38;
        --text: #e8e9ec;
        --muted: #9aa0ac;
        --accent: #4f8cff;
        --danger: #e2555a;
        --ok: #3ecf8e;
        --warn: #e8b64f;
    }
    * { box-sizing: border-box; }
    body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: var(--bg);
        color: var(--text);
        padding: 2rem 1rem;
    }
    .wrap { max-width: 680px; margin: 0 auto; }
    h1 { font-size: 1.4rem; margin-bottom: 0.25rem; }
    h2 { font-size: 1.1rem; margin: 0 0 0.75rem 0; }
    p.sub { color: var(--muted); margin-top: 0; margin-bottom: 1.5rem; font-size: 0.9rem; }
    section { margin-bottom: 2.5rem; }
    .card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
    }
    form.add-form { display: flex; gap: 0.5rem; }
    input[type=text] {
        flex: 1;
        padding: 0.6rem 0.75rem;
        border-radius: 8px;
        border: 1px solid var(--border);
        background: #0f1115;
        color: var(--text);
        font-size: 0.95rem;
    }
    input[type=text]:focus { outline: 2px solid var(--accent); }
    button {
        padding: 0.6rem 1rem;
        border-radius: 8px;
        border: none;
        background: var(--accent);
        color: white;
        font-size: 0.9rem;
        cursor: pointer;
    }
    button:hover { opacity: 0.9; }
    button.danger { background: transparent; color: var(--danger); border: 1px solid var(--danger); padding: 0.35rem 0.6rem; }
    ul { list-style: none; margin: 0; padding: 0; }
    li {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        padding: 0.6rem 0;
        border-bottom: 1px solid var(--border);
        font-size: 0.9rem;
    }
    li:last-child { border-bottom: none; }
    li .label { word-break: break-all; flex: 1; }
    li .actions { display: flex; align-items: center; gap: 0.6rem; flex-shrink: 0; }
    .empty { color: var(--muted); font-size: 0.9rem; padding: 0.5rem 0; }
    .flash {
        background: #1c3326;
        border: 1px solid #2c5c40;
        color: #8fd6ac;
        padding: 0.6rem 0.9rem;
        border-radius: 8px;
        margin-bottom: 1.25rem;
        font-size: 0.9rem;
    }
    .badge {
        font-size: 0.75rem;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        white-space: nowrap;
    }
    .badge.running { background: rgba(232, 182, 79, 0.15); color: var(--warn); }
    .badge.done { background: rgba(62, 207, 142, 0.15); color: var(--ok); }
    .badge.error { background: rgba(226, 85, 90, 0.15); color: var(--danger); }
    .badge.idle { background: rgba(154, 160, 172, 0.15); color: var(--muted); }
</style>
</head>
<body>
<div class="wrap">
    <h1>Mediathek-URLs</h1>
    <p class="sub">Serien laufen automatisch per Cron. Filme werden sofort beim Eintragen heruntergeladen.</p>

    {% if message %}
    <div class="flash">{{ message }}</div>
    {% endif %}

    <section>
        <h2>Serien &amp; Sendungen</h2>
        <div class="card">
            <form class="add-form" method="post" action="{{ url_for('add') }}">
                <input type="text" name="url" placeholder="https://www.ardmediathek.de/serie/..." required>
                <button type="submit">Hinzufügen</button>
            </form>
        </div>
        <div class="card">
            {% if urls %}
            <ul>
                {% for u in urls %}
                <li>
                    <span class="label">{{ u }}</span>
                    <form method="post" action="{{ url_for('delete', index=loop.index0) }}">
                        <button type="submit" class="danger">Entfernen</button>
                    </form>
                </li>
                {% endfor %}
            </ul>
            {% else %}
            <p class="empty">Noch keine Serien-URLs eingetragen.</p>
            {% endif %}
        </div>
    </section>

    <section>
        <h2>Filme</h2>
        <div class="card">
            <form class="add-form" method="post" action="{{ url_for('add_film') }}">
                <input type="text" name="url" placeholder="https://www.zdf.de/dokumentation/..." required>
                <button type="submit">Herunterladen</button>
            </form>
        </div>
        <div class="card">
            {% if filme %}
            <ul id="filme-list">
                {% for f in filme %}
                <li data-url="{{ f }}">
                    <span class="label">{{ f }}</span>
                    <span class="actions">
                        <span class="badge idle status-badge">wird geprüft…</span>
                        <form method="post" action="{{ url_for('delete_film', index=loop.index0) }}">
                            <button type="submit" class="danger">Entfernen</button>
                        </form>
                    </span>
                </li>
                {% endfor %}
            </ul>
            {% else %}
            <p class="empty">Noch keine Filme eingetragen.</p>
            {% endif %}
        </div>
    </section>
</div>

<script>
// Aktualisiert die Status-Badges der Filme alle 4 Sekunden, ohne die Seite neu zu laden
async function refreshFilmStatus() {
    try {
        const res = await fetch("{{ url_for('film_status') }}");
        const data = await res.json();
        document.querySelectorAll('#filme-list li').forEach(li => {
            const url = li.dataset.url;
            const badge = li.querySelector('.status-badge');
            const info = data[url];
            if (!info) {
                badge.textContent = "noch nicht gestartet";
                badge.className = "badge idle status-badge";
                return;
            }
            badge.textContent = info.label;
            badge.className = "badge " + info.status + " status-badge";
        });
    } catch (e) {
        // still fehlschlagen, kein UI-Absturz
    }
}
refreshFilmStatus();
setInterval(refreshFilmStatus, 4000);
</script>
</body>
</html>
"""


def read_list_file(path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Eine URL pro Zeile\n")
        return [], ["# Eine URL pro Zeile\n"]

    with open(path, "r", encoding="utf-8") as f:
        raw = f.readlines()

    comments = [line for line in raw if line.strip().startswith("#") or not line.strip()]
    entries = [line.strip() for line in raw if line.strip() and not line.strip().startswith("#")]
    return entries, comments


def write_list_file(path, entries, comments):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for c in comments:
            f.write(c if c.endswith("\n") else c + "\n")
        for e in entries:
            f.write(e + "\n")


def set_job_status(url, status, label):
    with film_jobs_lock:
        film_jobs[url] = {
            "status": status,
            "label": label,
            "updated": datetime.now().isoformat(timespec="seconds"),
        }


PERCENT_RE = re.compile(r"\[download\]\s+([\d.]+)%")


def run_film_download(url):
    set_job_status(url, "running", "wird gestartet…")
    os.makedirs(FILME_DIR, exist_ok=True)
    cmd = [
        "yt-dlp",
        "--newline",
        "-f", "bestvideo*+bestaudio/best",
        "--merge-output-format", "mp4",
        "--restrict-filenames",
        "--no-overwrites",
        "--download-archive", os.path.join(FILME_DIR, ".archive.txt"),
        "--embed-subs", "--sub-langs", "de.*,deu", "--write-subs",
        "--embed-metadata",
        "--embed-thumbnail",
        "--convert-thumbnails", "jpg",
        "--concurrent-fragments", "4",
        "-o", os.path.join(
            FILME_DIR,
            "%(title)s (%(release_year,upload_date>%Y)s)/%(title)s (%(release_year,upload_date>%Y)s) [%(id)s].%(ext)s",
        ),
        url,
    ]

    last_line = ""
    watchdog = None
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )

        # Sicherheitsnetz: nach 3 Stunden abbrechen, falls ein Download haengen bleibt
        watchdog = threading.Timer(3 * 3600, process.kill)
        watchdog.start()

        for line in process.stdout:
            last_line = line.strip()
            match = PERCENT_RE.search(line)
            if match:
                set_job_status(url, "running", f"{match.group(1)}%")
            elif "Merging formats" in line or "[Merger]" in line:
                set_job_status(url, "running", "wird zusammengeführt…")
            elif "[EmbedThumbnail]" in line or "[Metadata]" in line:
                set_job_status(url, "running", "Metadaten werden eingebettet…")

        process.wait()
        watchdog.cancel()

        if process.returncode == 0:
            set_job_status(url, "done", "fertig")
        else:
            set_job_status(url, "error", f"Fehler: {last_line[:80]}")
    except Exception as exc:  # noqa: BLE001
        if watchdog:
            watchdog.cancel()
        set_job_status(url, "error", f"Fehler: {exc}")


@app.route("/")
def index():
    urls, _ = read_list_file(URLS_FILE)
    filme, _ = read_list_file(FILME_URLS_FILE)
    message = request.args.get("message")
    return render_template_string(TEMPLATE, urls=urls, filme=filme, message=message)


@app.route("/add", methods=["POST"])
def add():
    new_url = request.form.get("url", "").strip()
    if new_url:
        urls, comments = read_list_file(URLS_FILE)
        if new_url not in urls:
            urls.append(new_url)
            write_list_file(URLS_FILE, urls, comments)
            return redirect(url_for("index", message="Serien-URL hinzugefügt."))
        return redirect(url_for("index", message="URL war schon eingetragen."))
    return redirect(url_for("index"))


@app.route("/delete/<int:index>", methods=["POST"])
def delete(index):
    urls, comments = read_list_file(URLS_FILE)
    if 0 <= index < len(urls):
        removed = urls.pop(index)
        write_list_file(URLS_FILE, urls, comments)
        return redirect(url_for("index", message=f"Entfernt: {removed}"))
    return redirect(url_for("index"))


@app.route("/add_film", methods=["POST"])
def add_film():
    new_url = request.form.get("url", "").strip()
    if new_url:
        filme, comments = read_list_file(FILME_URLS_FILE)
        if new_url not in filme:
            filme.append(new_url)
            write_list_file(FILME_URLS_FILE, filme, comments)
        set_job_status(new_url, "running", "wird heruntergeladen…")
        thread = threading.Thread(target=run_film_download, args=(new_url,), daemon=True)
        thread.start()
        return redirect(url_for("index", message="Download gestartet."))
    return redirect(url_for("index"))


@app.route("/delete_film/<int:index>", methods=["POST"])
def delete_film(index):
    filme, comments = read_list_file(FILME_URLS_FILE)
    if 0 <= index < len(filme):
        removed = filme.pop(index)
        write_list_file(FILME_URLS_FILE, filme, comments)
        with film_jobs_lock:
            film_jobs.pop(removed, None)
        return redirect(url_for("index", message=f"Entfernt: {removed}"))
    return redirect(url_for("index"))


@app.route("/api/film-status")
def film_status():
    with film_jobs_lock:
        return jsonify(dict(film_jobs))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
