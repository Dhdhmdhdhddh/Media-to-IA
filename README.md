# Media-to-IA

A tool to mass-archive media from YouTube and other platforms directly to the Internet Archive. Built for preserving historical footage of extreme weather events and other time-sensitive content at scale.

---

## Features

- Downloads from YouTube playlists, single videos, channels, and 1000+ other sites via yt-dlp
- Uploads directly to Internet Archive as a single organized collection
- Download → upload → delete loop keeps local storage usage minimal
- Combine multiple playlists/sources into one collection, automatically removing duplicate videos
- Sorts videos largest-first so big files don't end up stranded near a run's time limit
- Skips files over a configurable size limit (useful for avoiding long streams)
- Optional cap on number of videos processed per run (useful for large channels)
- Automatically retries failed uploads, and aborts a run early if too many fail in a row
- Tracks completed runs in `completed.json` so you never archive the same thing twice
- Logs per-video results in `log.json` for auditing and retrying failures later
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

### Workflows

This repo includes three workflows, all under the **Actions** tab:

| Workflow | What it does |
|----------|--------------|
| **Download and Upload to Internet Archive** | The main tool — downloads and archives media |
| **Show Archive Stats** | Prints a summary of everything archived so far |
| **Retry Failed Uploads** | Re-attempts any videos that previously failed to upload |

### Running the main workflow

1. Go to the **Actions** tab
2. Select **Download and Upload to Internet Archive**
3. Click **Run workflow**
4. Fill in the inputs:

| Input | Description |
|-------|-------------|
| URL(s) | One or more URLs — YouTube playlist, single video, channel, or any yt-dlp supported URL. For multiple sources, put each on its own line (or separate with commas) |
| Collection name | Name for the archive.org item. **Required** if you enter more than one URL. Leave blank for a single source to use its title automatically |
| Max file size (MB) | Skip files larger than this — default 200, set higher for longer videos |
| Max videos | Optional cap on how many videos to process — useful when pointing at a channel with a huge upload history |

5. Hit **Run workflow** and let it go

Results are posted in the Actions log with a direct link to your archive.org collection when done.

#### Archiving multiple sources as one collection

If you enter more than one URL (e.g. two overlapping playlists covering the same event), the tool will:

1. Fetch the video list from each source
2. Remove any duplicate videos that appear in more than one source (matched by video ID)
3. Archive the combined, deduplicated set under a single collection name

This is useful when multiple people have uploaded overlapping footage of the same event across different playlists.

### Checking stats

Run **Show Archive Stats** from the Actions tab. It reads `completed.json` and `log.json` and prints:

- total collections archived
- total videos uploaded / skipped / failed
- total size archived (in GB)
- a per-collection breakdown with archive.org links
- a warning if any videos are still failed and need retrying

### Retrying failures

If `stats` shows failed videos, run **Retry Failed Uploads**. It scans `log.json` for anything marked failed, re-downloads just those specific videos, and re-uploads each one to the correct original archive.org item.

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
python downloader.py "<URL(s)>" "[collection name]" "[max_mb]" "[cookies.txt]" "[node_path]" "[max_videos]"
```

URLs can be separated with newlines or commas for multi-source runs. `cookies.txt`, `node_path`, and `max_videos` are optional — Node is only needed for YouTube's JS challenge solving.

**Examples:**

```bash
# YouTube playlist, auto-named collection
python downloader.py "https://youtube.com/playlist?list=PLxxxxxx"

# Single video with custom collection name
python downloader.py "https://youtu.be/xxxxx" "Joplin EF5 2011"

# With size limit and cookies
python downloader.py "https://youtube.com/playlist?list=PLxxxxxx" "My Collection" "500" "cookies.txt"

# Multiple playlists combined into one deduplicated collection
python downloader.py "https://youtube.com/playlist?list=AAA,https://youtube.com/playlist?list=BBB" "Combined Collection"
```

To retry failures or check stats locally:

```bash
python retry_failed.py "[max_mb]" "[cookies.txt]" "[node_path]"
python stats.py
```

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

Every successfully completed run gets logged here with metadata:

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

Every run also logs a per-video breakdown, including title, video ID, source URL, file size, and status (`uploaded`, `upload_failed`, `skip_size`, `skip_no_file`, or an error message). This is what `stats.py` and `retry_failed.py` use to report on and fix individual videos without needing to re-run an entire collection.

---

## Supported sites

Anything yt-dlp supports — YouTube, Twitter/X, TikTok, Reddit, Twitch VODs, Facebook, Vimeo, and 1000+ more. YouTube gets special handling with cookie authentication and JS challenge solving. This might change in the future if new sites are added/become a focus.

---

## Disclaimer

Only archive content you have the right to distribute. Respect copyright laws and platform terms of service.
