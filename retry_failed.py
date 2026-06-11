"""
Retry failed uploads from log.json.

Scans log.json for any video entries with status 'upload_failed' or
starting with 'error', groups them by the identifier they belong to,
re-downloads each one and uploads it to the SAME archive.org item.

Usage:
  python retry_failed.py [max_mb] [cookiefile] [node_path]
"""

import yt_dlp
import os
import sys
import json
import time
import re
import tempfile
import internetarchive as ia

SAVE_PATH = os.path.join(tempfile.gettempdir(), 'media-to-ia-downloads')
LOG_FILE = 'log.json'
UPLOAD_DELAY = 15
UPLOAD_RETRIES = 2
RETRY_DELAY = 20

def is_youtube(url):
    return any(x in url for x in ['youtube.com', 'youtu.be'])

def clean_title(title):
    title = re.sub(r'#\w+', '', title)
    title = re.sub(r'@\w+', '', title)
    return ' '.join(title.split()).strip()

def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f'[err] failed to load {path}: {e}')
        return {}

def save_json(path, data):
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f'[err] failed to save {path}: {e}')

def make_opts(url, cookiefile, node_path):
    opts = {}
    if is_youtube(url):
        opts['extractor_args'] = {'youtube': {'player_client': ['web']}}
        if node_path:
            opts['js_runtimes'] = {'node': {'path': node_path}}
        if cookiefile:
            opts['cookiefile'] = cookiefile
    opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    opts['outtmpl'] = os.path.join(SAVE_PATH, '%(title)s [%(id)s].%(ext)s')
    opts['ignoreerrors'] = True
    opts['noplaylist'] = True
    return opts

def upload_file(filepath, identifier, collection_title, video_meta):
    filename = os.path.basename(filepath)
    print(f'    uploading {filename[:60]}...')

    description = 'Archived media'
    parts = []
    if video_meta.get('uploader'):
        parts.append(f"Original uploader: {video_meta['uploader']}")
    if video_meta.get('original_url'):
        parts.append(f"Original URL: {video_meta['original_url']}")
    if parts:
        description = ' | '.join(parts)

    metadata = {
        'title': collection_title,
        'mediatype': 'movies',
        'description': description,
        'creator': 'Media-to-IA',
        'date': time.strftime('%Y-%m-%d'),
    }
    if video_meta.get('original_url'):
        metadata['source'] = video_meta['original_url']

    for attempt in range(1, UPLOAD_RETRIES + 1):
        try:
            ia.upload(identifier, files=[filepath], metadata=metadata)
            print(f'    [ok] uploaded')
            return True
        except Exception as e:
            print(f'    [err] upload failed (attempt {attempt}/{UPLOAD_RETRIES}): {e}')
            if attempt < UPLOAD_RETRIES:
                print(f'    retrying in {RETRY_DELAY}s...')
                time.sleep(RETRY_DELAY)
    return False

def main():
    max_mb = float(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].strip() else 5000
    cookiefile = sys.argv[2] if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else None
    node_path = sys.argv[3] if len(sys.argv) > 3 and os.path.exists(sys.argv[3]) else None

    log_data = load_json(LOG_FILE)
    if not log_data:
        print('no log.json data found')
        return

    # collect failed videos grouped by (run_key, identifier, collection)
    jobs = []  # list of (run_key, identifier, collection_title, video_index, video_entry)
    for run_key, run in log_data.items():
        identifier = run.get('identifier')
        collection_title = run.get('collection')
        for idx, v in enumerate(run.get('videos', [])):
            status = v.get('status') or ''
            if status == 'upload_failed' or status.startswith('error'):
                jobs.append((run_key, identifier, collection_title, idx, v))

    if not jobs:
        print('no failed videos found in log.json — nothing to retry')
        return

    print(f'found {len(jobs)} failed video(s) to retry\n')
    os.makedirs(SAVE_PATH, exist_ok=True)

    retried = 0
    fixed = 0
    still_failed = 0

    for run_key, identifier, collection_title, idx, v in jobs:
        video_url = v.get('url')
        print(f'[{retried+1}/{len(jobs)}] retrying {video_url}')
        print(f'  -> {identifier}')
        retried += 1

        try:
            with yt_dlp.YoutubeDL(make_opts(video_url, cookiefile, node_path)) as ydl:
                vinfo = ydl.extract_info(video_url, download=True)

            files = [f for f in os.listdir(SAVE_PATH) if f.endswith(('.mp4', '.webm', '.m4a', '.mkv'))]
            if not files:
                print('  [skip] nothing downloaded')
                continue

            for f in files:
                filepath = os.path.join(SAVE_PATH, f)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)

                if size_mb > max_mb:
                    print(f'  [skip] {f[:50]} is {size_mb:.0f} MB — over limit')
                    os.remove(filepath)
                    continue

                video_meta = {
                    'uploader': vinfo.get('uploader') if vinfo else None,
                    'original_url': video_url,
                }
                success = upload_file(filepath, identifier, collection_title, video_meta)
                os.remove(filepath)

                if success:
                    fixed += 1
                    log_data[run_key]['videos'][idx]['status'] = 'uploaded'
                    log_data[run_key]['videos'][idx]['size_mb'] = round(size_mb, 1)
                else:
                    still_failed += 1

                time.sleep(UPLOAD_DELAY)

        except Exception as e:
            print(f'  [err] {e}')
            still_failed += 1

    save_json(LOG_FILE, log_data)

    print(f'\n=== retry done ===')
    print(f'retried: {retried}')
    print(f'fixed:   {fixed}')
    print(f'still failed: {still_failed}')

if __name__ == '__main__':
    main()
