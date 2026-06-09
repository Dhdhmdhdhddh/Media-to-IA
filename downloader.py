import yt_dlp
import os
import sys
import json
import time
import re
import tempfile
import internetarchive as ia

SAVE_PATH = os.path.join(tempfile.gettempdir(), 'media-to-ia-downloads')
COMPLETED_FILE = 'completed.json'
UPLOAD_DELAY = 15

def clean_title(title):
    title = re.sub(r'#\w+', '', title)
    title = re.sub(r'@\w+', '', title)
    return ' '.join(title.split()).strip()

def clean_identifier(title):
    ident = ''.join(c if c.isalnum() or c in '-_' else '-' for c in title)
    ident = re.sub(r'-+', '-', ident).strip('-')
    return ident[:80]

def load_completed():
    if not os.path.exists(COMPLETED_FILE):
        return {}
    try:
        with open(COMPLETED_FILE) as f:
            return json.load(f)
    except Exception as e:
        print(f'[err] failed to load completed.json: {e}')
        return {}

def save_completed(data):
    try:
        with open(COMPLETED_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f'[err] failed to save completed.json: {e}')

def upload_file(filepath, identifier, collection_title):
    filename = os.path.basename(filepath)
    print(f'  uploading {filename[:60]}...')
    try:
        ia.upload(
            identifier,
            files=[filepath],
            metadata={
                'title': collection_title,
                'mediatype': 'movies',
                'description': 'Tornado footage archive',
                'creator': 'Media-to-IA',
                'date': time.strftime('%Y-%m-%d'),
            }
        )
        print(f'  [ok] uploaded')
        return True
    except Exception as e:
        print(f'  [err] upload failed: {e}')
        return False

def main():
    if len(sys.argv) < 2:
        print('[err] no URL provided')
        print('usage: python downloader.py <url> [custom_name] [max_mb] [cookiefile]')
        sys.exit(1)

    url = sys.argv[1].strip()
    custom_name = sys.argv[2].strip() if len(sys.argv) > 2 and sys.argv[2].strip() else None
    max_mb = float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].strip() else 200
    cookiefile = sys.argv[4] if len(sys.argv) > 4 and os.path.exists(sys.argv[4]) else None

    if cookiefile:
        print(f'using cookies from {cookiefile}')
    else:
        print('no cookie file found — some videos may be blocked')

    # check if already done
    completed = load_completed()
    if url in completed:
        print(f'[skip] already completed: {url}')
        print(f'uploaded as: {completed[url]["collection"]}')
        sys.exit(0)

    os.makedirs(SAVE_PATH, exist_ok=True)

    print(f'\nfetching playlist info...')
    try:
        with yt_dlp.YoutubeDL({
            'quiet': True,
            'extract_flat': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }) as ydl:
            playlist_info = ydl.extract_info(url, download=False)
            entries = [e for e in playlist_info.get('entries', []) if e is not None]
            playlist_title = clean_title(playlist_info.get('title', 'untitled'))
            total = len(entries)
    except Exception as e:
        print(f'[err] failed to fetch playlist: {e}')
        sys.exit(1)

    if total == 0:
        print('[err] no videos found in playlist')
        sys.exit(1)

    collection_title = custom_name if custom_name else playlist_title
    identifier = clean_identifier(collection_title)

    print(f'playlist: {playlist_title}')
    print(f'videos: {total}')
    print(f'collection: {collection_title}')
    print(f'identifier: {identifier}')
    print(f'max file size: {max_mb} MB')
    print(f'mode: download-upload-delete\n')

    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, entry in enumerate(entries, 1):
        try:
            video_id = entry.get('id')
            video_url = entry.get('url') or f"https://www.youtube.com/watch?v={video_id}"
            print(f'[{i}/{total}] downloading...')

            ydl_opts = {
                'format': '18/best[ext=mp4]/best',
                'outtmpl': os.path.join(SAVE_PATH, '%(title)s.%(ext)s'),
                'ignoreerrors': True,
                'noplaylist': True,
                'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            }

            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(video_url, download=True)

            files = [f for f in os.listdir(SAVE_PATH) if f.endswith(('.mp4', '.webm', '.m4a'))]
            if not files:
                print(f'  [skip] nothing downloaded')
                skip_count += 1
                continue

            for f in files:
                filepath = os.path.join(SAVE_PATH, f)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)

                if size_mb > max_mb:
                    print(f'  [skip] {f[:50]} is {size_mb:.0f} MB — over {max_mb} MB limit')
                    os.remove(filepath)
                    skip_count += 1
                    continue

                print(f'  size: {size_mb:.1f} MB')
                success = upload_file(filepath, identifier, collection_title)
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                os.remove(filepath)
                print(f'  deleted local copy')

                if i < total:
                    print(f'  waiting {UPLOAD_DELAY}s...')
                    time.sleep(UPLOAD_DELAY)
        except Exception as e:
            print(f'  [err] processing video failed: {e}')
            fail_count += 1
            continue

    print(f'\n=== done ===')
    print(f'uploaded: {success_count}')
    print(f'skipped:  {skip_count}')
    print(f'failed:   {fail_count}')
    print(f'https://archive.org/details/{identifier}')

    completed[url] = {
        'collection': collection_title,
        'identifier': identifier,
        'uploaded': success_count,
        'skipped': skip_count,
        'failed': fail_count,
        'date': time.strftime('%Y-%m-%d'),
    }
    save_completed(completed)
    print(f'saved to completed.json')

if __name__ == '__main__':
    main()
