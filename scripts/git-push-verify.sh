#!/bin/sh
set -eu
git diff --quiet && git diff --cached --quiet
test -n "$(git remote)"
branch=$(git branch --show-current)
test "$(git rev-parse HEAD)" = "$(git rev-parse @{upstream})"
printf 'PASS git-push-verify %s\n' "$branch"
