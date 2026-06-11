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
                'description': 'Archived media',
                'creator': 'Media-to-IA',
                'date': time.strftime('%Y-%m-%d'),
            }
        )
        print(f'  [ok] uploaded')
        return True
    except Exception as e:
        print(f'  [err] upload failed: {e}')
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

def main():
    if len(sys.argv) < 2:
        print('[err] no URL provided')
        sys.exit(1)

    url = sys.argv[1].strip()
    custom_name = sys.argv[2].strip() if len(sys.argv) > 2 and sys.argv[2].strip() else None
    max_mb = float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].strip() else 200
    cookiefile = sys.argv[4] if len(sys.argv) > 4 and os.path.exists(sys.argv[4]) else None
    node_path = sys.argv[5] if len(sys.argv) > 5 and os.path.exists(sys.argv[5]) else None

    print(f'url: {url}')
    print(f'youtube: {is_youtube(url)}')
    if cookiefile:
        print(f'cookies: {cookiefile}')
    if node_path:
        print(f'node: {node_path}')

    completed = load_completed()
    if url in completed:
        print(f'[skip] already completed: {url}')
        print(f'uploaded as: {completed[url]["collection"]}')
        sys.exit(0)

    os.makedirs(SAVE_PATH, exist_ok=True)

    print(f'\nfetching info...')
    try:
        with yt_dlp.YoutubeDL(make_opts(url, cookiefile, node_path, flat=True)) as ydl:
            info = ydl.extract_info(url, download=False)
            is_playlist = info.get('_type') == 'playlist'
            playlist_title = clean_title(info.get('title', 'untitled'))

            if is_playlist:
                entries = [e for e in info.get('entries', []) if e is not None]
                total = len(entries)
                # for playlists use original URLs not flat entries
                video_urls = []
                for e in entries:
                    vid_id = e.get('id')
                    if is_youtube(url):
                        video_urls.append(f"https://www.youtube.com/watch?v={vid_id}")
                    else:
                        video_urls.append(e.get('url') or e.get('webpage_url', ''))
            else:
                total = 1
                video_urls = [url]

    except Exception as e:
        print(f'[err] failed to fetch info: {e}')
        sys.exit(1)

    collection_title = custom_name if custom_name else playlist_title
    identifier = clean_identifier(collection_title)

    print(f'title: {playlist_title}')
    print(f'videos: {total}')
    print(f'collection: {collection_title}')
    print(f'identifier: {identifier}')
    print(f'max file size: {max_mb} MB\n')

    # for playlists, sort: unknown-size videos first (original order),
    # then known-size videos largest to smallest
    if is_playlist and total > 1:
        print('checking video sizes to sort largest-first...')
        sized = []
        unknown = []
        size_opts = make_opts(video_urls[0], cookiefile, node_path, flat=False)
        size_opts['quiet'] = True
        size_opts['skip_download'] = True
        size_opts.pop('outtmpl', None)

        for idx, vurl in enumerate(video_urls):
            try:
                with yt_dlp.YoutubeDL({**size_opts}) as ydl:
                    vinfo = ydl.extract_info(vurl, download=False)
                size_bytes = vinfo.get('filesize') or vinfo.get('filesize_approx')
            except Exception:
                size_bytes = None

            if size_bytes:
                sized.append((size_bytes, vurl))
            else:
                unknown.append(vurl)

        sized.sort(key=lambda x: x[0], reverse=True)
        video_urls = unknown + [u for _, u in sized]
        print(f'sorted: {len(unknown)} unknown-size first, then {len(sized)} sorted largest to smallest\n')

    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, video_url in enumerate(video_urls, 1):
        try:
            print(f'[{i}/{total}] downloading {video_url[:60]}...')

            with yt_dlp.YoutubeDL(make_opts(video_url, cookiefile, node_path, flat=False)) as ydl:
                ydl.extract_info(video_url, download=True)

            files = [f for f in os.listdir(SAVE_PATH) if f.endswith(('.mp4', '.webm', '.m4a', '.mkv'))]
            if not files:
                print(f'  [skip] nothing downloaded')
                skip_count += 1
                continue

            for f in files:
                filepath = os.path.join(SAVE_PATH, f)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)

                if size_mb > max_mb:
                    print(f'  [skip] {f[:50]} is {size_mb:.0f} MB — over limit')
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
            print(f'  [err] {e}')
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
