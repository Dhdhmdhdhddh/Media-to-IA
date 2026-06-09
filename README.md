# Media-to-IA

Download YouTube playlists and upload them to the Internet Archive.

## Installation

```bash
pip install -r requirements.txt
ia configure
```

## Usage

```bash
python downloader.py <youtube_url> [custom_name] [max_mb]
```

**Examples:**
```bash
python downloader.py "https://www.youtube.com/playlist?list=PLxxxxxx"
python downloader.py "https://www.youtube.com/playlist?list=PLxxxxxx" "My Collection"
python downloader.py "https://www.youtube.com/playlist?list=PLxxxxxx" "My Collection" 500
```

## How it works

1. Downloads videos from a YouTube playlist
2. Uploads to Internet Archive
3. Tracks completed uploads in `completed.json`
4. Deletes local files after successful upload

## Output

- Upload statistics
- Direct link to collection on archive.org
- Entry saved in `completed.json`
