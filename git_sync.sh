#!/bin/bash
# Helper script to sync changes to git
git add .
git commit -m "Auto-update: New content and sitemaps $(date +'%Y-%m-%d %H:%M:%S')"
git push origin main
