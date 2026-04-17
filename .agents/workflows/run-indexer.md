---
description: Run Google Indexer locally (200 links per run), then add, commit and push changes
---

# Google Indexer Workflow

Run this workflow to index the next 200 URLs via the Google Indexing API, then push the updated progress file.

## Steps

// turbo
1. Run the indexer script:
```bash
cd /home/tomito/tomito && python google_indexer.py
```

// turbo
2. Check progress and stage changes:
```bash
cd /home/tomito/tomito && git add indexer_progress.json && git status
```

// turbo
3. Commit and push:
```bash
cd /home/tomito/tomito && git commit -m "🔍 indexer: update progress after 200-link run" && git push
```
