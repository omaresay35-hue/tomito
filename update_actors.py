#!/usr/bin/env python3
"""
update_actors.py — Regenerate existing actor pages with filmography.
Reads all actor IDs from /actor/ folder.
Adds top 100 movies + top 100 TV shows per actor.
Does NOT add new actors.
"""

import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import shared functions from mega_bot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mega_bot import create_actor_page, BASE_PATH

ACTOR_DIR = os.path.join(BASE_PATH, 'actor')

def get_existing_actor_ids():
    """Extract actor IDs from existing HTML filenames in /actor/."""
    ids = []
    for fname in os.listdir(ACTOR_DIR):
        if fname.endswith('.html'):
            match = re.match(r'^(\d+)-', fname)
            if match:
                ids.append(int(match.group(1)))
    return ids

def main():
    actor_ids = get_existing_actor_ids()
    total = len(actor_ids)
    print(f"=== UPDATE ACTORS — Found {total} existing actor pages ===")

    done_count = [0]
    error_count = [0]

    def process(aid):
        try:
            result = create_actor_page(aid)
            done_count[0] += 1
            if done_count[0] % 100 == 0:
                print(f"  Progress: {done_count[0]}/{total} updated...")
            return result
        except Exception as e:
            error_count[0] += 1
            return None

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(process, aid) for aid in actor_ids]
        for f in as_completed(futures):
            pass

    print(f"\n✅ Done: {done_count[0]} actor pages updated")
    print(f"❌ Errors: {error_count[0]}")

if __name__ == '__main__':
    main()
