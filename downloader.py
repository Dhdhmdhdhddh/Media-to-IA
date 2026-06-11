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
LOG_FILE = 'log.json'
UPLOAD_DELAY = 15
MAX_CONSECUTIVE_FAILS = 10
UPLOAD_RETRIES = 2  # total attempts per file
RETRY_DELAY = 20

def is_youtube(url):
    return any(x in url for x in ['youtube.com', 'youtu.be'])

def clean_title(title):
    title = re.sub(r'#\w+', '', title)
    title = re.sub(r'@\w+', '', title)
    return ' '.join(title.split()).strip()

def clean_identifier(title):
    ident = ''.join(c if c.isalnum() or c in '-_' else '-' for c in title)
    ident = re.sub(r'-+', '-', ident).strip('-')
    return ident[:80]

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

def upload_file(filepath, identifier, collection_title, video_meta):
    filename = os.path.basename(filepath)
    print(f'  uploading {filename[:60]}...')

    description = 'Archived media'
    if video_meta:
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
    if video_meta and video_meta.get('original_url'):
        metadata['source'] = video_meta['original_url']

    for attempt in range(1, UPLOAD_RETRIES + 1):
        try:
            ia.upload(identifier, files=[filepath], metadata=metadata)
            print(f'  [ok] uploaded')
            return True
        except Exception as e:
            print(f'  [err] upload failed (attempt {attempt}/{UPLOAD_RETRIES}): {e}')
            if attempt < UPLOAD_RETRIES:
                print(f'  retrying in {RETRY_DELAY}s...')
                time.sleep(RETRY_DELAY)

    return False

def make_opts(url, cookiefile, node_path, flat=False):
    opts = {}

    if is_youtube(url):
        opts['extractor_args'] = {'youtube': {'player_client': ['web']}}
        if node_path:
            opts['js_runtimes'] = {'node': {'path': node_path}}
        if cookiefile:
            opts['cookiefile'] = cookiefile

    if flat:
        opts['quiet'] = True
        opts['extract_flat'] = True
    else:
        opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        opts['outtmpl'] = os.path.join(SAVE_PATH, '%(title)s [%(id)s].%(ext)s')
        opts['ignoreerrors'] = True
        opts['noplaylist'] = True

    return opts

def split_urls(raw):
    """Split input on newlines and commas, strip whitespace, drop empties."""
    parts = re.split(r'[\n,]+', raw)
    return [p.strip() for p in parts if p.strip()]

def fetch_source(url, cookiefile, node_path):
    """
    Fetch a single source URL (playlist or single video).
    Returns (title, list_of_video_dicts) where each video dict has:
      {'id': ..., 'url': ..., 'title': ..., 'uploader': ...}
    """
    with yt_dlp.YoutubeDL(make_opts(url, cookiefile, node_path, flat=True)) as ydl:
        info = ydl.extract_info(url, download=False)

    title = clean_title(info.get('title', 'untitled'))
    is_playlist = info.get('_type') == 'playlist'

    videos = []
    if is_playlist:
        entries = [e for e in info.get('entries', []) if e is not None]
        for e in entries:
            vid_id = e.get('id')
            if is_youtube(url):
                vurl = f"https://www.youtube.com/watch?v={vid_id}"
            else:
                vurl = e.get('url') or e.get('webpage_url', '')
            videos.append({
                'id': vid_id,
                'url': vurl,
                'title': e.get('title', 'untitled'),
                'uploader': e.get('uploader') or e.get('channel'),
            })
    else:
        videos.append({
            'id': info.get('id'),
            'url': url,
            'title': info.get('title', 'untitled'),
            'uploader': info.get('uploader'),
        })

    return title, videos

def main():
    if len(sys.argv) < 2:
        print('[err] no URL provided')
        sys.exit(1)

    raw_url = sys.argv[1].strip()
    custom_name = sys.argv[2].strip() if len(sys.argv) > 2 and sys.argv[2].strip() else None
    max_mb = float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].strip() else 200
    cookiefile = sys.argv[4] if len(sys.argv) > 4 and os.path.exists(sys.argv[4]) else None
    node_path = sys.argv[5] if len(sys.argv) > 5 and os.path.exists(sys.argv[5]) else None

    source_urls = split_urls(raw_url)
    multi = len(source_urls) > 1

    # the completed.json key is the raw input as given (so re-running with the
    # same exact input, single or multi, is detected as a duplicate)
    completed_key = raw_url

    print(f'sources: {len(source_urls)}')
    for u in source_urls:
        print(f'  - {u}')
    if cookiefile:
        print(f'cookies: {cookiefile}')
    if node_path:
        print(f'node: {node_path}')

    completed = load_json(COMPLETED_FILE)
    if completed_key in completed:
        print(f'[skip] already completed')
        print(f'uploaded as: {completed[completed_key]["collection"]}')
        sys.exit(0)

    log_data = load_json(LOG_FILE)

    os.makedirs(SAVE_PATH, exist_ok=True)

    print(f'\nfetching info...')
    first_title = None
    seen_ids = set()
    videos = []  # deduplicated list of video dicts
    dup_count = 0

    try:
        for src_url in source_urls:
            title, src_videos = fetch_source(src_url, cookiefile, node_path)
            if first_title is None:
                first_title = title
            print(f'  "{title}": {len(src_videos)} videos')
            for v in src_videos:
                vid_id = v.get('id')
                key = vid_id if vid_id else v['url']
                if key in seen_ids:
                    dup_count += 1
                    continue
                seen_ids.add(key)
                videos.append(v)
    except Exception as e:
        print(f'[err] failed to fetch info: {e}')
        sys.exit(1)

    if multi and dup_count:
        print(f'  removed {dup_count} duplicate video(s) found across sources')

    total = len(videos)
    if total == 0:
        print('[err] no videos found')
        sys.exit(1)

    if multi and not custom_name:
        print('[err] a collection name is required when combining multiple sources')
        sys.exit(1)

    collection_title = custom_name if custom_name else first_title
    identifier = clean_identifier(collection_title)
    is_playlist = total > 1

    print(f'\ncollection: {collection_title}')
    print(f'identifier: {identifier}')
    print(f'videos: {total}')
    print(f'max file size: {max_mb} MB\n')

    # for multi-video sets, sort: unknown-size videos first (original order),
    # then known-size videos largest to smallest
    if is_playlist:
        print('checking video sizes to sort largest-first...')
        sized = []
        unknown = []
        size_opts = make_opts(videos[0]['url'], cookiefile, node_path, flat=False)
        size_opts['quiet'] = True
        size_opts['skip_download'] = True
        size_opts.pop('outtmpl', None)

        for v in videos:
            try:
                with yt_dlp.YoutubeDL({**size_opts}) as ydl:
                    vinfo = ydl.extract_info(v['url'], download=False)
                size_bytes = vinfo.get('filesize') or vinfo.get('filesize_approx')
            except Exception:
                size_bytes = None

            if size_bytes:
                sized.append((size_bytes, v))
            else:
                unknown.append(v)

        sized.sort(key=lambda x: x[0], reverse=True)
        videos = unknown + [v for _, v in sized]
        print(f'sorted: {len(unknown)} unknown-size first, then {len(sized)} sorted largest to smallest\n')

    success_count = 0
    skip_count = 0
    fail_count = 0
    consecutive_fails = 0
    aborted = False
    run_log = []

    for i, video in enumerate(videos, 1):
        video_url = video['url']
        entry_log = {'url': video_url, 'status': None, 'title': video.get('title'), 'id': video.get('id'), 'size_mb': None}
        try:
            print(f'[{i}/{total}] downloading {video_url[:60]}...')

            with yt_dlp.YoutubeDL(make_opts(video_url, cookiefile, node_path, flat=False)) as ydl:
                vinfo = ydl.extract_info(video_url, download=True)

            video_title = clean_title(vinfo.get('title', '')) if vinfo else video.get('title')
            video_uploader = vinfo.get('uploader') if vinfo else video.get('uploader')
            entry_log['title'] = video_title
            entry_log['id'] = vinfo.get('id') if vinfo else video.get('id')

            files = [f for f in os.listdir(SAVE_PATH) if f.endswith(('.mp4', '.webm', '.m4a', '.mkv'))]
            if not files:
                print(f'  [skip] nothing downloaded')
                skip_count += 1
                entry_log['status'] = 'skip_no_file'
                run_log.append(entry_log)
                continue

            for f in files:
                filepath = os.path.join(SAVE_PATH, f)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                entry_log['size_mb'] = round(size_mb, 1)

                if size_mb > max_mb:
                    print(f'  [skip] {f[:50]} is {size_mb:.0f} MB — over limit')
                    os.remove(filepath)
                    skip_count += 1
                    entry_log['status'] = 'skip_size'
                    continue

                print(f'  size: {size_mb:.1f} MB')

                video_meta = {
                    'uploader': video_uploader,
                    'original_url': video_url,
                }
                success = upload_file(filepath, identifier, collection_title, video_meta)
                if success:
                    success_count += 1
                    consecutive_fails = 0
                    entry_log['status'] = 'uploaded'
                else:
                    fail_count += 1
                    consecutive_fails += 1
                    entry_log['status'] = 'upload_failed'
                os.remove(filepath)
                print(f'  deleted local copy')

                if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
                    print(f'\n[abort] {consecutive_fails} consecutive upload failures — stopping run')
                    aborted = True

                if i < total:
                    print(f'  waiting {UPLOAD_DELAY}s...')
                    time.sleep(UPLOAD_DELAY)

            run_log.append(entry_log)

            if aborted:
                break
        except Exception as e:
            print(f'  [err] {e}')
            fail_count += 1
            consecutive_fails += 1
            entry_log['status'] = f'error: {e}'
            run_log.append(entry_log)
            if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
                print(f'\n[abort] {consecutive_fails} consecutive upload failures — stopping run')
                aborted = True
                break
            continue

    print(f'\n=== done ===')
    if aborted:
        print(f'status: ABORTED after {MAX_CONSECUTIVE_FAILS} consecutive failures')
    print(f'uploaded: {success_count}')
    print(f'skipped:  {skip_count}')
    print(f'failed:   {fail_count}')
    if multi:
        print(f'duplicates removed across sources: {dup_count}')
    print(f'https://archive.org/details/{identifier}')

    log_data[completed_key] = {
        'collection': collection_title,
        'identifier': identifier,
        'sources': source_urls,
        'duplicates_removed': dup_count,
        'aborted': aborted,
        'date': time.strftime('%Y-%m-%d'),
        'videos': run_log,
    }
    save_json(LOG_FILE, log_data)
    print(f'saved per-video log to {LOG_FILE}')

    if not aborted:
        completed[completed_key] = {
            'collection': collection_title,
            'identifier': identifier,
            'sources': source_urls,
            'uploaded': success_count,
            'skipped': skip_count,
            'failed': fail_count,
            'date': time.strftime('%Y-%m-%d'),
        }
        save_json(COMPLETED_FILE, completed)
        print(f'saved to {COMPLETED_FILE}')
    else:
        print(f'NOT marked as completed due to abort — fix the issue and re-run')
        sys.exit(1)

if __name__ == '__main__':
    main()
