# Media-to-IA

A tool to mass-archive media from YouTube and other platforms directly to the Internet Archive. Built for preserving historical footage of extreme weather events and other time-sensitive content at scale.

---

## Features

- Downloads from YouTube playlists, single videos, and 1000+ other sites via yt-dlp
- Uploads directly to Internet Archive as a single organized collection
- Download → upload → delete loop keeps local storage usage minimal
- Skips files over a configurable size limit (useful for avoiding long streams)
- Tracks completed URLs in `completed.json` so you never archive the same thing twice
- Runs entirely on GitHub Actions — no local setup needed for bulk archiving

---

## GitHub Actions (recommended)

This is the main way to use the tool. Everything runs on GitHub's servers so you don't need to leave your device on.

### Setup

1. Fork or clone this repo
2. Add the following secrets under **Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `IA_EMAIL` | Your archive.org email |
| `IA_PASSWORD` | Your archive.org password |
| `YT_COOKIES` | Contents of your YouTube `cookies.txt` (needed to get around bot detection) |

3. Go to **Settings → Actions → General → Workflow permissions** and set to **Read and write permissions**

### Running

1. Go to the **Actions** tab
2. Select **Download and Upload to Internet Archive**
3. Click **Run workflow**
4. Fill in the inputs:

| Input | Description |
|-------|-------------|
| URL | YouTube playlist or video URL (or any yt-dlp supported URL) |
| Collection name | Name for the archive.org item (leave blank to use the playlist title) |
| Max file size (MB) | Skip files larger than this — default 200, set higher for longer videos |

5. Hit **Run workflow** and let it go

Results are posted in the Actions log with a direct link to your archive.org collection when done.

---

## Local / Pydroid Usage

You can also run the script locally or on Android via Pydroid 3.

### Install dependencies

```bash
pip install "yt-dlp[default]" internetarchive
```

### Configure Internet Archive

```bash
ia configure
```

### Run

```bash
python downloader.py "<URL>" "[collection name]" "[max_mb]" "[cookies.txt]"
```

**Examples:**

```bash
# YouTube playlist, auto-named collection
python downloader.py "https://youtube.com/playlist?list=PLxxxxxx"

# Single video with custom collection name
python downloader.py "https://youtu.be/xxxxx" "Joplin EF5 2011"

# With size limit and cookies
python downloader.py "https://youtube.com/playlist?list=PLxxxxxx" "My Collection" "500" "cookies.txt"
```

---

## How it works

1. Fetches playlist/video info
2. Downloads each video one at a time
3. Uploads it to archive.org under one collection identifier
4. Deletes the local copy
5. Moves to the next video
6. Logs the completed URL to `completed.json` when finished

---

## completed.json

Every successfully archived URL gets logged here with metadata:

```json
{
  "https://youtube.com/playlist?list=PLxxxxxx": {
    "collection": "My Collection",
    "identifier": "My-Collection",
    "uploaded": 19,
    "skipped": 2,
    "failed": 0,
    "date": "2026-06-10"
  }
}
```

Running the same URL again will be skipped automatically.

---

## Supported sites

Anything yt-dlp supports — YouTube, Twitter/X, TikTok, Reddit, Twitch VODs, Facebook, Vimeo, and 1000+ more. YouTube gets special handling with cookie authentication and JS challenge solving. This might change in the future if new sites are added/become a focus.

---

## Disclaimer

Only archive content you have the right to distribute. Respect copyright laws and platform terms of service.
