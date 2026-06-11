"""
Print a summary of everything archived so far based on completed.json
and log.json.

Usage:
  python stats.py
"""

import json
import os

COMPLETED_FILE = 'completed.json'
LOG_FILE = 'log.json'

def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}

def main():
    completed = load_json(COMPLETED_FILE)
    log_data = load_json(LOG_FILE)

    total_collections = len(completed)
    total_uploaded = sum(c.get('uploaded', 0) for c in completed.values())
    total_skipped = sum(c.get('skipped', 0) for c in completed.values())
    total_failed = sum(c.get('failed', 0) for c in completed.values())

    # total size from log.json (only uploaded videos have size_mb recorded)
    total_mb = 0
    for run in log_data.values():
        for v in run.get('videos', []):
            if v.get('status') == 'uploaded' and v.get('size_mb'):
                total_mb += v['size_mb']

    total_gb = total_mb / 1024

    print('=== Media-to-IA stats ===\n')
    print(f'collections archived: {total_collections}')
    print(f'videos uploaded:      {total_uploaded}')
    print(f'videos skipped:       {total_skipped}')
    print(f'videos failed:        {total_failed}')
    print(f'total size archived:  {total_gb:.2f} GB ({total_mb:.0f} MB)\n')

    if completed:
        print('--- collections ---')
        for url, c in completed.items():
            print(f"  {c.get('collection', '?')}")
            print(f"    https://archive.org/details/{c.get('identifier', '?')}")
            print(f"    uploaded: {c.get('uploaded', 0)}, skipped: {c.get('skipped', 0)}, failed: {c.get('failed', 0)}, date: {c.get('date', '?')}")

    # any failures still outstanding
    outstanding = 0
    for run in log_data.values():
        for v in run.get('videos', []):
            status = v.get('status') or ''
            if status == 'upload_failed' or status.startswith('error'):
                outstanding += 1

    if outstanding:
        print(f'\n[!] {outstanding} video(s) still failed in log.json — run retry_failed.py to retry them')

if __name__ == '__main__':
    main()
