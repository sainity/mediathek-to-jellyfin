# Mediathek-to-Jellyfin — Automated German Public Broadcasting Downloader & Home Media Server

[![Build container images](https://github.com/sainity/<repo-name>/actions/workflows/build-images.yml/badge.svg)](https://github.com/sainity/<repo-name>/actions/workflows/build-images.yml)
[![Lint](https://github.com/sainity/<repo-name>/actions/workflows/lint.yml/badge.svg)](https://github.com/sainity/<repo-name>/actions/workflows/lint.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*(After pushing to GitHub, replace `sainity/<repo-name>` in the two badge URLs above with your actual GitHub path so they render correctly.)*

Automatically download content from German public broadcasting (ÖRR) media libraries — ARD Mediathek, ZDF Mediathek, arte, 3sat, and others — and serve it through a self-hosted [Jellyfin](https://jellyfin.org/) media server, all running as Docker containers on a QNAP NAS.

This repository bundles everything built in an iterative setup process into one place: a scheduled downloader, a manual download trigger with a web UI, and a Jellyfin deployment, plus the folder conventions that tie them together.

> **Legal note:** Downloading content from ARD/ZDF/arte/3sat media libraries for private, personal use is explicitly permitted — these broadcasters provide open interfaces (used by tools like [MediathekView](https://mediathekview.de/)) specifically for this purpose. This project is intended for personal archiving only. Do not redistribute downloaded content or make it available to third parties; respect the applicable terms of use and copyright law in your jurisdiction.

---

## What's in here

| Component | What it does |
|---|---|
| `docker-compose.yml` | Deploys Jellyfin + the two custom containers below as one stack |
| `mediathek-dl/` | Docker image with `yt-dlp` + a lightweight cron replacement (`supercronic`) that automatically downloads new episodes of shows you subscribe to, on a schedule |
| `mediathek-web/` | A small Flask web UI to manage the list of subscribed shows, and to trigger one-off movie downloads with a live progress indicator |
| `systemd-alternative/` | The same download scripts as standalone systemd user services/timers, for people who want to run this on a plain Linux desktop instead of in Docker on a NAS |

## Architecture

```
                     ┌─────────────────────────────┐
                     │        QNAP NAS (QTS)        │
                     │      Container Station        │
                     │                               │
   Browser  ───────▶ │  ┌────────────┐               │
   :8199             │  │  Jellyfin   │◀── reads ──┐  │
                      │  └────────────┘             │  │
   Browser  ───────▶ │  ┌────────────┐              │  │
   :8098             │  │mediathek-web│── writes ───┤  │
                      │  └────────────┘              │  │
                      │  ┌────────────┐              │  │
                      │  │mediathek-dl │── writes ───┘  │
                      │  │  (cron)     │                │
                      │  └────────────┘                 │
                      │         │                        │
                      │  /share/<MEDIA_SHARE>/               │
                      │    ├── Filme/                      │
                      │    ├── Serien/                      │
                      │    └── Mediathek/Shows/               │
                      └─────────────────────────────────────┘
```

## Prerequisites

- A QNAP NAS with **Container Station** installed (QTS 5.x recommended). This should also work on other Docker-capable NAS/Linux hosts with minor path adjustments.
- SSH access enabled on the NAS (Control Panel → Network & File Services → Telnet/SSH), and an account with either `sudo` rights or the ability to log in as `admin`. Several build/permission steps require root.
- Enough free storage on the NAS for your media library. Downloads are not re-encoded to save space; they're stored at their original (best available) quality.
- Basic comfort with the command line (`ssh`, `scp`).
- x86_64 CPU on the NAS (the container images are built for `amd64`). Most QNAP models with Intel Celeron CPUs qualify; ARM-based QNAP models are not covered by this setup as-is.
- *(Optional, for hardware transcoding)* An Intel CPU with an integrated GPU exposed at `/dev/dri` (e.g. the TS-x53/x64/x73 series). Not required — Jellyfin works fine with software transcoding, just with more CPU load.

## Repository layout

```
.
├── docker-compose.yml          # Full stack: Jellyfin + mediathek-dl + mediathek-web
├── mediathek-dl/                # Scheduled downloader (runs inside Docker via cron)
│   ├── Dockerfile
│   ├── crontab
│   ├── mediathek-dl.sh          # Core yt-dlp wrapper, best quality, for series
│   ├── mediathek-batch.sh       # Reads urls.txt and downloads each show
│   ├── mediathek-check.sh       # Checks for new episodes without downloading
│   └── mediathek-film-dl.sh     # Variant for standalone movies (Jellyfin "Movies" naming)
├── mediathek-web/                # Web UI for managing subscriptions + on-demand movie downloads
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
└── systemd-alternative/          # Same idea, without Docker/NAS — plain systemd timers
    ├── mediathek-dl.sh
    ├── mediathek-batch.sh
    ├── mediathek-check.sh
    ├── mediathek-dl.service / .timer
    └── mediathek-check.service / .timer
```

## Placeholders you must replace

This repository ships with generic placeholders instead of any specific NAS setup, since paths, ports, and user IDs are unique to every installation. Before deploying, replace these everywhere they appear (`docker-compose.yml` and, if you copy commands from this README, in your terminal):

| Placeholder | Meaning | Example |
|---|---|---|
| `<MEDIA_SHARE>` | Your NAS share name for media (movies, shows, Mediathek downloads) | `Multimedia` |
| `<CONTAINER_SHARE>` | Your NAS share name for container configuration/state | `Container` |
| `<UID>:<GID>` | Your NAS user's numeric user/group ID, so containers can write to your shares without running as root | `1000:100` |
| `<NAS-IP>` | Your NAS's IP address or hostname | `192.168.1.62` |

`docker-compose.yml` has a short reminder comment at the top listing these too. The ports `8199` (Jellyfin) and `8098` (management UI) are plain example values, not placeholders — **check whether they're already in use on your NAS and change them in `docker-compose.yml` if so** (see the port-conflict entries under Troubleshooting for what that looks like in practice).

## Step-by-step installation (QNAP + Docker)

### 1. Prepare the NAS shares

Create (or reuse) a shared folder for your media, e.g. `Multimedia`, with this subfolder layout:

```
/share/<MEDIA_SHARE>/
├── Filme/       # Standalone movies/documentaries (Jellyfin "Movies" library)
├── Serien/      # Regular TV shows you rip/own with proper season/episode metadata
└── Mediathek/
    └── Shows/   # Everything downloaded automatically from the ÖRR media libraries
```

Also create a folder for the containers' own configuration/state:

```bash
ssh admin@<NAS-IP>
mkdir -p /share/<CONTAINER_SHARE>/jellyfin/config
mkdir -p /share/<CONTAINER_SHARE>/jellyfin/cache
mkdir -p /share/<CONTAINER_SHARE>/mediathek-dl/config
mkdir -p /share/<CONTAINER_SHARE>/mediathek-dl
mkdir -p /share/<CONTAINER_SHARE>/mediathek-web
```

Find your NAS user's UID/GID (needed so containers can write to these folders without running as root):

```bash
id <your-nas-username>
# e.g. uid=1000(Christian_A) gid=100(everyone)
```

Set ownership accordingly (as `admin`/root if a normal user's `chown` fails with "Operation not permitted"):

```bash
chown -R <uid>:<gid> /share/<CONTAINER_SHARE>/jellyfin/config /share/<CONTAINER_SHARE>/jellyfin/cache
chown -R <uid>:<gid> /share/<CONTAINER_SHARE>/mediathek-dl/config
```

Update the `user: "<UID>:<GID>"` lines in `docker-compose.yml` to match your actual UID:GID if they differ.

### 2. Copy the repository to the NAS

From your local machine:

```bash
scp -r ./mediathek-dl admin@<NAS-IP>:/share/<CONTAINER_SHARE>/mediathek-dl-src
scp -r ./mediathek-web admin@<NAS-IP>:/share/<CONTAINER_SHARE>/mediathek-web-src
scp ./docker-compose.yml admin@<NAS-IP>:/share/<CONTAINER_SHARE>/jellyfin/docker-compose.yml
```

(Adjust folder names to taste — the important part is that the Dockerfile and its accompanying scripts end up together in one folder, since `docker build` uses the current directory as its build context.)

### 3. Build the two custom images

```bash
ssh admin@<NAS-IP>
cd /share/<CONTAINER_SHARE>/mediathek-dl-src
sudo docker build -t mediathek-dl:latest .

cd /share/<CONTAINER_SHARE>/mediathek-web-src
sudo docker build -t mediathek-web:latest .
```

### 4. Adjust `docker-compose.yml` to your environment

Open the file and check/adjust:
- All `/share/...` paths to match your actual NAS share names (visible in File Station)
- The Web UI port (`8199` for Jellyfin, `8098` for the management UI) in case they're already taken on your NAS
- The `user: "uid:gid"` lines to match your actual account (step 1)
- The `devices: /dev/dri:/dev/dri` block: only uncomment if your NAS model has a supported Intel GPU (see Troubleshooting)

### 5. Start the stack

```bash
cd /share/<CONTAINER_SHARE>/jellyfin
sudo docker compose up -d
docker ps
```

All three containers (`jellyfin`, `mediathek-dl`, `mediathek-web`) should show status `Up`.

> If your NAS doesn't have the `docker-compose`/`docker compose` CLI available, use Container Station's GUI instead: **Create → Create Application**, paste the contents of `docker-compose.yml`, and click **Create**. This avoids CLI availability issues entirely.

### 6. Set up Jellyfin

Open `http://<NAS-IP>:8199` (or whichever port you chose) and complete the setup wizard. Then add three libraries under **Dashboard → Libraries → Add Library**:

| Library | Content type | Path (inside container) | Metadata providers |
|---|---|---|---|
| Movies | Movies | `/media/Filme` | TheMovieDb: **on** |
| TV Shows | Shows | `/media/Serien` | TheTVDB/TheMovieDb: **on** |
| Mediathek | Shows | `/media/Mediathek/Shows` | **off** (embedded metadata from yt-dlp is used instead) |

### 7. Add subscriptions and start downloading

Open the management UI at `http://<NAS-IP>:8098`:

- **Series & shows** section: paste the URL of a show/season overview page (not a single-episode URL — see below). These are downloaded automatically every night (default: 04:00), with a "new episodes available" check every 6 hours.
- **Movies** section: paste the URL of a single documentary/film. This triggers an immediate background download with a live progress percentage.

## Folder naming conventions used by the scripts

**Mediathek shows** (`mediathek-dl.sh` / cron):
```
Mediathek/Shows/<Show Name>/<Show Name> - <YYYY-MM-DD> - <Episode Title> [<id>].mp4
```

**Standalone movies** (`mediathek-film-dl.sh` / web UI):
```
Filme/<Title> (<Year>)/<Title> (<Year>) [<id>].mp4
```

**Regular TV series you manage yourself** (not automated by this project, but expected by the Jellyfin library):
```
Serien/<Show Name> (<Year>)/Season 01/<Show Name> S01E01 - <Episode Title>.mkv
```

## Finding the right URL to subscribe to a whole season

A direct link to a single episode only downloads that one episode. To grab a whole season automatically, you need the *season/series overview page*:

1. Open the single episode you found and click through to the series/season overview (usually the show's title, which links to a `/serie/...` URL rather than `/video/...`).
2. Test it before adding it permanently:
   ```bash
   docker exec -it mediathek-dl yt-dlp --flat-playlist --print "%(id)s - %(title)s" "<URL>"
   ```
   If this prints multiple lines (one per episode), it's a valid playlist URL — use it. If it prints just one line, it's a single episode.

## Configuration reference

| Variable | Used by | Default | Purpose |
|---|---|---|---|
| `MEDIATHEK_DIR` | `mediathek-dl`, `mediathek-batch.sh` | `/media/Mediathek` | Root folder for automated show downloads |
| `FILME_DIR` | `mediathek-film-dl.sh`, `mediathek-web` | `/media/Filme` | Root folder for movie downloads |
| `URLS_FILE` | `mediathek-web` | `/config/urls.txt` | List of subscribed show/season URLs |
| `FILME_URLS_FILE` | `mediathek-web` | `/config/filme.txt` | History of movie URLs added via the web UI |

## Troubleshooting

This section documents the actual issues encountered while building this setup, in case you hit the same ones.

**`the attribute 'version' is obsolete`**
Harmless warning from newer `docker compose` versions. Safe to ignore, or just remove the `version:` line from the compose file.

**`failed to bind port 0.0.0.0:1900/udp` / `:7359/udp`**
QNAP's own DLNA/media-streaming service already occupies these ports. Either disable it (Control Panel → Multimedia Management → disable DLNA Media Server) or remove those optional port mappings from `docker-compose.yml` — Jellyfin works fine without them, you just lose SSDP-based auto-discovery in some client apps.

**`Access to the path '/config/log' is denied'`**
The container runs as a non-root user (`user: "uid:gid"` in the compose file), but the host folder mounted at `/config` is still owned by root. Fix ownership on the NAS side:
```bash
chown -R <uid>:<gid> /share/<CONTAINER_SHARE>/jellyfin/config /share/<CONTAINER_SHARE>/jellyfin/cache
```

**`mkdir: cannot create directory '/root': Permission denied'`**
Same root cause as above, but for the `mediathek-dl` container: it runs as a non-root user, so it can't write to `/root`. The Dockerfile creates a dedicated `/home/mediathek` directory owned by UID 1000 instead — make sure the host-side config folder mounted into it is owned by the matching UID:GID.

**`docker-compose: command not found`**
Newer Container Station versions ship the Docker Compose *plugin* instead, invoked as `docker compose` (space, not hyphen). Try that first. If neither is available, use the Container Station GUI's "Create Application" flow instead, which has its own built-in Compose parser.

**`apt-get install cron` fails during image build with a `systemd` postinst error (exit code 100)**
On newer Debian-based base images, the `cron` package pulls in `systemd` as a dependency, and `systemd`'s post-install script fails inside a Docker build environment (no real init system available). This project sidesteps the issue entirely by using [`supercronic`](https://github.com/aptible/supercronic) instead of the `cron`/`systemd` combo — a small static binary purpose-built for running cron schedules inside containers, with no such dependency.

**`chown: Operation not permitted`**
Regular NAS user accounts, even ones in the `administrators` group, often can't `chown` files outside their own home directory. Either prefix the command with `sudo`, or log in via SSH as the classic `admin` account, which has full root access.

**Firefox: `SSL_ERROR_RX_RECORD_TOO_LONG`**
This means the browser tried HTTPS against a plain HTTP port. Jellyfin serves HTTP by default on the port you mapped (e.g. `8199`) — make sure you're navigating to `http://`, not `https://`, and check whether your browser has an "HTTPS-only mode" forcing the upgrade.

## Optional: hardware transcoding

If your NAS has a supported Intel iGPU (e.g. UHD 600 on the Celeron J4005 in the TS-251D), you can enable VAAPI-based hardware transcoding to reduce CPU load:

1. Uncomment the `devices: - /dev/dri:/dev/dri` block for the `jellyfin` service in `docker-compose.yml`.
2. Restart the stack.
3. In Jellyfin: **Dashboard → Playback → Transcoding**, set hardware acceleration to **VAAPI**, device `/dev/dri/renderD128`, and enable hardware decoding for H264/HEVC/VP9 plus hardware encoding for H264.

If the container fails to start with a permission error on `/dev/dri`, add your NAS's `video` group GID (`getent group video`) to the `group_add` section of the `jellyfin` service.

## Optional: running without Docker/NAS (systemd alternative)

If you'd rather run the downloader directly on a Linux desktop (e.g. Fedora/Nobara) instead of on a NAS, see `systemd-alternative/`. It provides the same scripts as plain systemd **user** services/timers:

```bash
mkdir -p ~/.local/bin
cp systemd-alternative/mediathek-dl.sh systemd-alternative/mediathek-batch.sh systemd-alternative/mediathek-check.sh ~/.local/bin/
chmod +x ~/.local/bin/mediathek-*.sh

mkdir -p ~/.config/systemd/user
cp systemd-alternative/*.service systemd-alternative/*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now mediathek-dl.timer
systemctl --user enable --now mediathek-check.timer
```

This variant has no web UI; manage `~/.config/mediathek-dl/urls.txt` directly with a text editor.

## Credits & underlying tools

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — the actual downloader engine
- [Jellyfin](https://jellyfin.org/) — the media server
- [supercronic](https://github.com/aptible/supercronic) — container-friendly cron
- [MediathekView](https://mediathekview.de/) — the original inspiration and GUI alternative for browsing/downloading ÖRR content

## License

This repository's own scripts and configuration are provided under the MIT License (see `LICENSE`). This does **not** grant any rights to the downloaded media content itself, which remains subject to the copyright of its respective broadcasters.
