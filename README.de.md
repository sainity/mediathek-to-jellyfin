# Mediathek-to-Jellyfin — Automatischer ÖRR-Mediathek-Downloader & eigener Medienserver

[![Build container images](https://github.com/sainity/<repo-name>/actions/workflows/build-images.yml/badge.svg)](https://github.com/sainity/<repo-name>/actions/workflows/build-images.yml)
[![Lint](https://github.com/sainity/<repo-name>/actions/workflows/lint.yml/badge.svg)](https://github.com/sainity/<repo-name>/actions/workflows/lint.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

*(Nach dem Push auf GitHub `sainity/<repo-name>` in den beiden Badge-URLs oben durch deinen tatsächlichen GitHub-Pfad ersetzen, damit sie korrekt angezeigt werden.)*

Lädt automatisch Inhalte aus den Mediatheken der öffentlich-rechtlichen Rundfunkanstalten (ÖRR) — ARD Mediathek, ZDF Mediathek, arte, 3sat u. a. — herunter und stellt sie über einen selbst gehosteten [Jellyfin](https://jellyfin.org/)-Medienserver bereit. Alles läuft als Docker-Container auf einem QNAP NAS.

Dieses Repository bündelt alles, was in einem schrittweisen Aufbauprozess entstanden ist: ein automatisierter, zeitgesteuerter Downloader, ein manueller Download-Auslöser mit Weboberfläche, sowie ein Jellyfin-Deployment inklusive der Ordnerkonventionen, die alles miteinander verbindet.

> **Rechtlicher Hinweis:** Das Herunterladen von Inhalten aus den Mediatheken von ARD/ZDF/arte/3sat für den privaten, persönlichen Gebrauch ist ausdrücklich erlaubt — die Sender stellen dafür offene Schnittstellen bereit (die z. B. auch [MediathekView](https://mediathekview.de/) nutzt). Dieses Projekt ist ausschließlich für die private Archivierung gedacht. Heruntergeladene Inhalte dürfen nicht weiterverbreitet oder Dritten zugänglich gemacht werden; beachte die jeweils geltenden Nutzungsbedingungen und das Urheberrecht.

---

## Was ist enthalten

| Komponente | Aufgabe |
|---|---|
| `docker-compose.yml` | Startet Jellyfin sowie die beiden folgenden eigenen Container als einen zusammenhängenden Stack |
| `mediathek-dl/` | Docker-Image mit `yt-dlp` und einem schlanken Cron-Ersatz (`supercronic`), der automatisch neue Folgen abonnierter Sendungen zeitgesteuert herunterlädt |
| `mediathek-web/` | Eine kleine Flask-Weboberfläche zum Verwalten der abonnierten Sendungen sowie zum direkten Auslösen von Film-Downloads mit Live-Fortschrittsanzeige |
| `systemd-alternative/` | Dieselben Download-Skripte als eigenständige systemd-User-Services/-Timer, für alle, die das Ganze lieber auf einem normalen Linux-Desktop statt per Docker auf einer NAS betreiben möchten |

## Architektur

```
                     ┌─────────────────────────────┐
                     │        QNAP NAS (QTS)        │
                     │      Container Station        │
                     │                               │
   Browser  ───────▶ │  ┌────────────┐               │
   :8199             │  │  Jellyfin   │◀── liest ───┐  │
                      │  └────────────┘             │  │
   Browser  ───────▶ │  ┌────────────┐              │  │
   :8098             │  │mediathek-web│── schreibt ─┤  │
                      │  └────────────┘              │  │
                      │  ┌────────────┐              │  │
                      │  │mediathek-dl │── schreibt ─┘  │
                      │  │  (cron)     │                │
                      │  └────────────┘                 │
                      │         │                        │
                      │  /share/<MEDIA_SHARE>/               │
                      │    ├── Filme/                      │
                      │    ├── Serien/                      │
                      │    └── Mediathek/Shows/               │
                      └─────────────────────────────────────┘
```

## Voraussetzungen

- Ein QNAP NAS mit installierter **Container Station** (QTS 5.x empfohlen). Sollte mit kleineren Pfadanpassungen auch auf anderen Docker-fähigen NAS-/Linux-Systemen funktionieren.
- Aktivierter SSH-Zugriff auf der NAS (Systemsteuerung → Netzwerk & Dateidienste → Telnet/SSH) sowie ein Konto mit `sudo`-Rechten oder die Möglichkeit, sich als `admin` einzuloggen. Mehrere Build-/Berechtigungsschritte benötigen Root-Rechte.
- Ausreichend freier Speicherplatz auf der NAS für deine Mediensammlung. Downloads werden nicht neu kodiert, um Platz zu sparen — sie werden in der besten verfügbaren Originalqualität gespeichert.
- Grundlegende Vertrautheit mit der Kommandozeile (`ssh`, `scp`).
- x86_64-CPU auf der NAS (die Container-Images sind für `amd64` gebaut). Die meisten QNAP-Modelle mit Intel-Celeron-CPUs erfüllen das; ARM-basierte QNAP-Modelle werden von diesem Setup so nicht abgedeckt.
- *(Optional, für Hardware-Transcoding)* Eine Intel-CPU mit integrierter GPU, erreichbar unter `/dev/dri` (z. B. TS-x53/x64/x73-Serie). Nicht zwingend erforderlich — Jellyfin funktioniert auch mit Software-Transcoding einwandfrei, nur mit höherer CPU-Last.

## Aufbau des Repositories

```
.
├── docker-compose.yml          # Kompletter Stack: Jellyfin + mediathek-dl + mediathek-web
├── mediathek-dl/                # Zeitgesteuerter Downloader (läuft per Cron im Container)
│   ├── Dockerfile
│   ├── crontab
│   ├── mediathek-dl.sh          # Zentraler yt-dlp-Wrapper, beste Qualität, für Serien
│   ├── mediathek-batch.sh       # Liest urls.txt und lädt jede Sendung herunter
│   ├── mediathek-check.sh       # Prüft auf neue Folgen, ohne herunterzuladen
│   └── mediathek-film-dl.sh     # Variante für Einzelfilme (Jellyfin-"Filme"-Benennung)
├── mediathek-web/                # Weboberfläche zur Verwaltung von Abos + Filme auf Abruf
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
└── systemd-alternative/          # Gleiches Prinzip, ohne Docker/NAS — reine systemd-Timer
    ├── mediathek-dl.sh
    ├── mediathek-batch.sh
    ├── mediathek-check.sh
    ├── mediathek-dl.service / .timer
    └── mediathek-check.service / .timer
```

## Platzhalter, die du ersetzen musst

Dieses Repository enthält bewusst generische Platzhalter statt eines konkreten NAS-Setups, da Pfade, Ports und Benutzer-IDs bei jeder Installation anders sind. Ersetze vor dem Deployment überall folgende Werte (in der `docker-compose.yml` sowie in deinem Terminal, falls du Befehle aus diesem README kopierst):

| Platzhalter | Bedeutung | Beispiel |
|---|---|---|
| `<MEDIA_SHARE>` | Name deiner NAS-Freigabe für Medien (Filme, Serien, Mediathek-Downloads) | `Multimedia` |
| `<CONTAINER_SHARE>` | Name deiner NAS-Freigabe für Container-Konfiguration/-Status | `Container` |
| `<UID>:<GID>` | Numerische User-/Gruppen-ID deines NAS-Benutzers, damit Container ohne Root-Rechte in deine Freigaben schreiben können | `1000:100` |
| `<NAS-IP>` | IP-Adresse oder Hostname deiner NAS | `192.168.1.62` |

Die `docker-compose.yml` enthält oben ebenfalls einen kurzen Erinnerungskommentar dazu. Die Ports `8199` (Jellyfin) und `8098` (Verwaltungsoberfläche) sind reine Beispielwerte, keine Platzhalter — **prüfe, ob sie auf deiner NAS schon belegt sind, und ändere sie bei Bedarf in der `docker-compose.yml`** (siehe die Port-Konflikt-Einträge unter Fehlerbehebung, wie sich das in der Praxis zeigt).

## Schritt-für-Schritt-Installation (QNAP + Docker)

### 1. NAS-Freigaben vorbereiten

Lege eine Freigabe für deine Mediensammlung an (oder nutze eine bestehende), z. B. `Multimedia`, mit folgender Unterordnerstruktur:

```
/share/<MEDIA_SHARE>/
├── Filme/       # Einzelne Filme/Dokumentationen (Jellyfin-Bibliothek "Filme")
├── Serien/      # Reguläre Serien mit sauberen Staffel-/Folgen-Metadaten
└── Mediathek/
    └── Shows/   # Alles, was automatisch aus den ÖRR-Mediatheken geladen wird
```

Lege außerdem einen Ordner für die Konfiguration/den Zustand der Container an:

```bash
ssh admin@<NAS-IP>
mkdir -p /share/<CONTAINER_SHARE>/jellyfin/config
mkdir -p /share/<CONTAINER_SHARE>/jellyfin/cache
mkdir -p /share/<CONTAINER_SHARE>/mediathek-dl/config
mkdir -p /share/<CONTAINER_SHARE>/mediathek-dl
mkdir -p /share/<CONTAINER_SHARE>/mediathek-web
```

Ermittle die UID/GID deines NAS-Benutzers (nötig, damit die Container ohne Root-Rechte in diese Ordner schreiben können):

```bash
id <dein-benutzername>
# z.B. uid=1000(Christian_A) gid=100(everyone)
```

Setze die Besitzrechte entsprechend (als `admin`/root, falls `chown` als normaler Benutzer mit "Operation not permitted" fehlschlägt):

```bash
chown -R <uid>:<gid> /share/<CONTAINER_SHARE>/jellyfin/config /share/<CONTAINER_SHARE>/jellyfin/cache
chown -R <uid>:<gid> /share/<CONTAINER_SHARE>/mediathek-dl/config
```

Passe die Zeilen `user: "<UID>:<GID>"` in der `docker-compose.yml` an deine tatsächliche UID:GID an, falls sie abweicht.

### 2. Repository auf die NAS kopieren

Von deinem lokalen Rechner aus:

```bash
scp -r ./mediathek-dl admin@<NAS-IP>:/share/<CONTAINER_SHARE>/mediathek-dl-src
scp -r ./mediathek-web admin@<NAS-IP>:/share/<CONTAINER_SHARE>/mediathek-web-src
scp ./docker-compose.yml admin@<NAS-IP>:/share/<CONTAINER_SHARE>/jellyfin/docker-compose.yml
```

(Ordnernamen nach Belieben anpassen — wichtig ist nur, dass Dockerfile und die zugehörigen Skripte gemeinsam in einem Ordner landen, da `docker build` das aktuelle Verzeichnis als Build-Kontext verwendet.)

### 3. Die beiden eigenen Images bauen

```bash
ssh admin@<NAS-IP>
cd /share/<CONTAINER_SHARE>/mediathek-dl-src
sudo docker build -t mediathek-dl:latest .

cd /share/<CONTAINER_SHARE>/mediathek-web-src
sudo docker build -t mediathek-web:latest .
```

### 4. `docker-compose.yml` an deine Umgebung anpassen

Datei öffnen und prüfen/anpassen:
- Alle `/share/...`-Pfade an deine tatsächlichen Freigabenamen anpassen (sichtbar in File Station)
- Die Ports der Weboberflächen (`8199` für Jellyfin, `8098` für die Verwaltungsoberfläche), falls sie auf deiner NAS schon belegt sind
- Die `user: "uid:gid"`-Zeilen an dein tatsächliches Konto anpassen (Schritt 1)
- Den Block `devices: /dev/dri:/dev/dri`: nur einkommentieren, wenn dein NAS-Modell eine unterstützte Intel-GPU besitzt (siehe Fehlerbehebung)

### 5. Den Stack starten

```bash
cd /share/<CONTAINER_SHARE>/jellyfin
sudo docker compose up -d
docker ps
```

Alle drei Container (`jellyfin`, `mediathek-dl`, `mediathek-web`) sollten den Status `Up` anzeigen.

> Falls auf deiner NAS keine `docker-compose`-/`docker compose`-CLI verfügbar ist, nutze stattdessen die GUI von Container Station: **Erstellen → Anwendung erstellen**, den Inhalt der `docker-compose.yml` einfügen und auf **Erstellen** klicken. So umgehst du CLI-Verfügbarkeitsprobleme komplett.

### 6. Jellyfin einrichten

Öffne `http://<NAS-IP>:8199` (oder den von dir gewählten Port) und durchlaufe den Einrichtungsassistenten. Lege dann unter **Dashboard → Bibliotheken → Bibliothek hinzufügen** drei Bibliotheken an:

| Bibliothek | Inhaltstyp | Pfad (im Container) | Metadatenanbieter |
|---|---|---|---|
| Filme | Filme | `/media/Filme` | TheMovieDb: **an** |
| Serien | Serien | `/media/Serien` | TheTVDB/TheMovieDb: **an** |
| Mediathek | Serien | `/media/Mediathek/Shows` | **aus** (stattdessen werden die von yt-dlp eingebetteten Metadaten genutzt) |

### 7. Abos anlegen und Downloads starten

Öffne die Verwaltungsoberfläche unter `http://<NAS-IP>:8098`:

- **Bereich "Serien & Sendungen":** URL einer Sendungs-/Staffel-Übersichtsseite eintragen (nicht die URL einer Einzelfolge — siehe unten). Diese werden automatisch jede Nacht heruntergeladen (Standard: 4 Uhr), mit einem Check auf neue Folgen alle 6 Stunden.
- **Bereich "Filme":** URL einer einzelnen Dokumentation/eines Films eintragen. Das löst sofort einen Download im Hintergrund mit Live-Fortschrittsanzeige in Prozent aus.

## Von den Skripten verwendete Ordner-Namenskonventionen

**Mediathek-Sendungen** (`mediathek-dl.sh` / Cron):
```
Mediathek/Shows/<Sendungsname>/<Sendungsname> - <JJJJ-MM-TT> - <Folgentitel> [<id>].mp4
```

**Einzelne Filme** (`mediathek-film-dl.sh` / Web-UI):
```
Filme/<Titel> (<Jahr>)/<Titel> (<Jahr>) [<id>].mp4
```

**Reguläre Serien, die du selbst verwaltest** (nicht durch dieses Projekt automatisiert, aber von der Jellyfin-Bibliothek erwartet):
```
Serien/<Serienname> (<Jahr>)/Season 01/<Serienname> S01E01 - <Folgentitel>.mkv
```

## Die richtige URL finden, um eine ganze Staffel zu abonnieren

Ein Direktlink zu einer einzelnen Folge lädt auch nur diese eine Folge herunter. Um automatisch eine ganze Staffel zu bekommen, brauchst du die *Staffel-/Serien-Übersichtsseite*:

1. Öffne die gefundene Einzelfolge und klick dich zur Serien-/Staffelübersicht durch (meist über den Serientitel, der auf eine `/serie/...`-URL statt `/video/...` verweist).
2. Vor dem dauerhaften Eintragen testen:
   ```bash
   docker exec -it mediathek-dl yt-dlp --flat-playlist --print "%(id)s - %(title)s" "<URL>"
   ```
   Kommen mehrere Zeilen zurück (eine pro Folge), ist es eine gültige Playlist-URL — die kannst du verwenden. Kommt nur eine Zeile, ist es eine Einzelfolge.

## Konfigurationsreferenz

| Variable | Verwendet von | Standard | Zweck |
|---|---|---|---|
| `MEDIATHEK_DIR` | `mediathek-dl`, `mediathek-batch.sh` | `/media/Mediathek` | Zielordner für automatisierte Sendungs-Downloads |
| `FILME_DIR` | `mediathek-film-dl.sh`, `mediathek-web` | `/media/Filme` | Zielordner für Film-Downloads |
| `URLS_FILE` | `mediathek-web` | `/config/urls.txt` | Liste der abonnierten Sendungs-/Staffel-URLs |
| `FILME_URLS_FILE` | `mediathek-web` | `/config/filme.txt` | Verlauf der über die Web-UI hinzugefügten Film-URLs |

## Fehlerbehebung

Dieser Abschnitt dokumentiert die tatsächlich beim Aufbau dieses Setups aufgetretenen Probleme, falls du auf dieselben stößt.

**`the attribute 'version' is obsolete`**
Harmlose Warnung neuerer `docker compose`-Versionen. Kann ignoriert werden, oder die `version:`-Zeile einfach aus der Compose-Datei entfernen.

**`failed to bind port 0.0.0.0:1900/udp` / `:7359/udp`**
QNAPs eigener DLNA-/Media-Streaming-Dienst belegt diese Ports bereits. Entweder deaktivieren (Systemsteuerung → Multimedia-Verwaltung → DLNA-Medienserver deaktivieren) oder die entsprechenden optionalen Portmappings aus der `docker-compose.yml` entfernen — Jellyfin funktioniert auch ohne, nur die automatische Server-Erkennung (SSDP) entfällt in manchen Client-Apps.

**`Access to the path '/config/log' is denied'`**
Der Container läuft als Nicht-Root-Benutzer (`user: "uid:gid"` in der Compose-Datei), der eingebundene Host-Ordner unter `/config` gehört aber noch root. Besitzrechte auf der NAS-Seite korrigieren:
```bash
chown -R <uid>:<gid> /share/<CONTAINER_SHARE>/jellyfin/config /share/<CONTAINER_SHARE>/jellyfin/cache
```

**`mkdir: cannot create directory '/root': Permission denied'`**
Gleiche Ursache wie oben, aber beim `mediathek-dl`-Container: Er läuft als Nicht-Root-Benutzer und darf daher nicht nach `/root` schreiben. Das Dockerfile legt stattdessen ein eigenes, UID 1000 gehörendes Verzeichnis `/home/mediathek` an — stelle sicher, dass der dort eingebundene NAS-Ordner der passenden UID:GID gehört.

**`docker-compose: command not found`**
Neuere Container-Station-Versionen liefern stattdessen das Docker-Compose-*Plugin* mit, aufgerufen als `docker compose` (mit Leerzeichen, nicht Bindestrich). Das zuerst probieren. Falls beides fehlt, stattdessen die "Anwendung erstellen"-GUI von Container Station nutzen, die einen eigenen, eingebauten Compose-Parser mitbringt.

**`apt-get install cron` schlägt beim Image-Build mit einem `systemd`-Postinstall-Fehler fehl (Exit-Code 100)**
Auf neueren Debian-basierten Basisimages zieht das `cron`-Paket `systemd` als Abhängigkeit mit rein, und dessen Post-Install-Skript scheitert innerhalb einer Docker-Build-Umgebung (kein echtes Init-System vorhanden). Dieses Projekt umgeht das Problem komplett, indem es [`supercronic`](https://github.com/aptible/supercronic) statt der Kombination `cron`/`systemd` verwendet — eine kleine, statische Binary, die speziell für Cron-Zeitpläne in Containern gebaut wurde und keine solche Abhängigkeit hat.

**`chown: Operation not permitted`**
Normale NAS-Benutzerkonten, selbst solche in der Gruppe `administrators`, können oft keine Dateien außerhalb ihres eigenen Home-Verzeichnisses per `chown` bearbeiten. Entweder den Befehl mit `sudo` voranstellen, oder sich per SSH als klassisches `admin`-Konto einloggen, das vollen Root-Zugriff besitzt.

**Firefox: `SSL_ERROR_RX_RECORD_TOO_LONG`**
Das bedeutet, der Browser hat HTTPS gegen einen reinen HTTP-Port versucht. Jellyfin liefert standardmäßig HTTP auf dem gemappten Port (z. B. `8199`) — stelle sicher, dass du `http://` statt `https://` aufrufst, und prüfe, ob dein Browser einen "Nur-HTTPS-Modus" erzwingt.

## Optional: Hardware-Transcoding

Falls deine NAS eine unterstützte Intel-iGPU besitzt (z. B. UHD 600 beim Celeron J4005 in der TS-251D), kannst du VAAPI-basiertes Hardware-Transcoding aktivieren, um die CPU-Last zu senken:

1. Den Block `devices: - /dev/dri:/dev/dri` beim `jellyfin`-Service in der `docker-compose.yml` einkommentieren.
2. Den Stack neu starten.
3. In Jellyfin: **Dashboard → Wiedergabe → Transcoding**, Hardware-Beschleunigung auf **VAAPI** setzen, Gerät `/dev/dri/renderD128`, Hardware-Decodierung für H264/HEVC/VP9 sowie Hardware-Encodierung für H264 aktivieren.

Falls der Container mit einem Berechtigungsfehler auf `/dev/dri` nicht startet, die GID der `video`-Gruppe deiner NAS (`getent group video`) zum `group_add`-Abschnitt des `jellyfin`-Services hinzufügen.

## Optional: Betrieb ohne Docker/NAS (systemd-Alternative)

Falls du den Downloader lieber direkt auf einem Linux-Desktop (z. B. Fedora/Nobara) statt auf einer NAS betreiben willst, sieh dir `systemd-alternative/` an. Dort liegen dieselben Skripte als reine systemd-**User**-Services/-Timer vor:

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

Diese Variante hat keine Weboberfläche; die `~/.config/mediathek-dl/urls.txt` wird direkt mit einem Texteditor verwaltet.

## Credits & verwendete Werkzeuge

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — die eigentliche Download-Engine
- [Jellyfin](https://jellyfin.org/) — der Medienserver
- [supercronic](https://github.com/aptible/supercronic) — containertauglicher Cron-Ersatz
- [MediathekView](https://mediathekview.de/) — die ursprüngliche Inspiration und grafische Alternative zum Durchsuchen/Herunterladen von ÖRR-Inhalten

## Lizenz

Die eigenen Skripte und Konfigurationsdateien dieses Repositories stehen unter der MIT-Lizenz (siehe `LICENSE`). Dies gewährt **keine** Rechte an den heruntergeladenen Medieninhalten selbst — diese unterliegen weiterhin dem Urheberrecht der jeweiligen Sender.
