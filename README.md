# Media-to-IA (Local)

A tool to mass-archive media from YouTube and other platforms directly to the Internet Archive, run locally or on Android via Pydroid 3. Built for preserving historical footage of extreme weather events and other time-sensitive content at scale.

This branch is the local/offline version — no GitHub Actions, no `.github/workflows/` folder. Everything runs directly on your own device.

---

## Features

- Downloads from YouTube playlists, single videos, channels, and 1000+ other sites via yt-dlp
- Uploads directly to Internet Archive as a single organized collection
- Download → upload → delete loop keeps local storage usage minimal
- Combine multiple playlists/sources into one collection, automatically removing duplicate videos
- Sorts videos largest-first so big files get handled before smaller ones
- Skips files over a configurable size limit (useful for avoiding long streams)
- Optional cap on number of videos processed per run (useful for large channels)
- Automatically retries failed uploads, and aborts a run early if too many fail in a row
- Tracks completed runs in `completed.json` so you never archive the same thing twice
- Logs per-video results in `log.json` for auditing and retrying failures later

---

## Setup

### Install dependencies

```bash
pip install "yt-dlp[default]" internetarchive
```

On Pydroid 3, run this in the Pydroid terminal/pip tab.

### Node.js (for YouTube)

YouTube requires solving a JS challenge to download with cookies. If you have Node.js installed, pass its path in (see usage below). Without Node, most non-age-restricted YouTube videos and other sites will still work fine.

### Configure Internet Archive

```bash
ia configure
```

This will ask for your archive.org email and password and store them locally.

### YouTube cookies (optional but recommended)

For age-restricted or region-locked YouTube videos, export your cookies to a `cookies.txt` file (e.g. using a browser extension like "Get cookies.txt"). Pass the path to this file in when running the script.

---

## Running

```bash
python downloader.py "<URL(s)>" "[collection name]" "[max_mb]" "[cookies.txt]" "[node_path]" "[max_videos]"
```

All arguments after the URL are optional.

| Argument | Description |
|----------|-------------|
| URL(s) | One or more URLs. For multiple sources, separate with newlines or commas — duplicates across them are removed automatically |
| collection name | Name for the archive.org item. **Required** if you pass more than one URL. Leave blank for a single source to use its title |
| max_mb | Skip files larger than this size in MB (default 200) |
| cookies.txt | Path to a YouTube cookies file |
| node_path | Path to your Node.js binary, for YouTube's JS challenge solving |
| max_videos | Cap on how many videos to process — useful for channels |

### Examples

```bash
# YouTube playlist, auto-named collection
python downloader.py "https://youtube.com/playlist?list=PLxxxxxx"

# Single video with custom collection name
python downloader.py "https://youtu.be/xxxxx" "Joplin EF5 2011"

# With size limit and cookies
python downloader.py "https://youtube.com/playlist?list=PLxxxxxx" "My Collection" "500" "cookies.txt"

# Multiple playlists combined into one deduplicated collection
python downloader.py "https://youtube.com/playlist?list=AAA,https://youtube.com/playlist?list=BBB" "Combined Collection"

# With cookies and Node for full YouTube support
python downloader.py "https://youtu.be/xxxxx" "My Video" "1000" "cookies.txt" "/usr/bin/node"
```

---

## Checking stats

```bash
python stats.py
```

Prints a summary of everything archived so far: total collections, total videos uploaded/skipped/failed, total size archived in GB, a per-collection breakdown with archive.org links, and a note if anything still needs retrying.

---

## Retrying failures

```bash
python retry_failed.py "[max_mb]" "[cookies.txt]" "[node_path]"
```

Scans `log.json` for any videos that previously failed to upload, re-downloads just those, and re-uploads each to its correct original archive.org item.

---

## How it works

1. Fetches info for each source URL
2. Combines and deduplicates videos across sources (if multiple were given)
3. Sorts videos so unknown-size videos go first, then largest to smallest
4. Downloads each video one at a time
5. Uploads it to archive.org under one collection identifier, with metadata including the original uploader and source URL
6. Deletes the local copy
7. Retries a failed upload once before giving up on that video; aborts the whole run if 10 uploads in a row fail
8. Logs per-video results to `log.json` and the overall run summary to `completed.json`

---

## completed.json

Every successfully completed run gets logged here:

```json
{
  "https://youtube.com/playlist?list=PLxxxxxx": {
    "collection": "My Collection",
    "identifier": "My-Collection",
    "sources": ["https://youtube.com/playlist?list=PLxxxxxx"],
    "uploaded": 19,
    "skipped": 2,
    "failed": 0,
    "date": "2026-06-10"
  }
}
```

Running the exact same input again will be skipped automatically. A run that aborts due to repeated failures is **not** marked as completed, so it can be safely re-run later.

---

## log.json

Every run also logs a per-video breakdown, including title, video ID, source URL, file size, and status (`uploaded`, `upload_failed`, `skip_size`, `skip_no_file`, or an error message). This is what `stats.py` and `retry_failed.py` use to report on and fix individual videos without re-running an entire collection.

---

## Supported sites

Anything yt-dlp supports — YouTube, Twitter/X, TikTok, Reddit, Twitch VODs, Facebook, Vimeo, and 1000+ more. YouTube gets special handling with cookie authentication and JS challenge solving when cookies/Node are provided.

---

## Storage tips (mobile/low storage devices)

The download → upload → delete loop means only one video sits on disk at a time, so even large playlists won't fill up your storage. If a single video exceeds your `max_mb` limit, it's skipped entirely (not partially downloaded).

---

## Disclaimer

Only archive content you have the right to distribute. Respect copyright laws and platform terms of service.
