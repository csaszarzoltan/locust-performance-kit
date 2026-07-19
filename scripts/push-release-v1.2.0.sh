#!/bin/bash
# Complete the v1.2.0 release push to GitHub
# Prerequisites: gh auth login OR GITHUB_TOKEN env var OR SSH key configured
set -e

REPO=/home/zoltan/locust-performance-kit
cd "$REPO"

echo "=== Pushing main branch ==="
git push origin main

echo "=== Pushing v1.2.0 tag ==="
git push origin v1.2.0

echo "=== Creating GitHub Release ==="
gh release create v1.2.0 \
  --title "v1.2.0 — Cross-platform report export" \
  --notes-file RELEASE_NOTES_v1.2.0.md

echo "=== Deleting remote feature branch (if exists) ==="
git push origin --delete feature/cross-platform-report-export 2>/dev/null || echo "Feature branch not on remote (already clean)"

echo "=== Verifying ==="
echo "Tags on origin:"
git ls-remote --tags origin | grep v1.2.0
echo ""
echo "Release:"
gh release view v1.2.0 --json name,tagName,createdAt

echo ""
echo "=== v1.2.0 release complete! ==="
