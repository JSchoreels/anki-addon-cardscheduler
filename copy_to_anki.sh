#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target_dir="/Users/jschoreels/Library/Application Support/Anki2/addons21/card-scheduler"
stage_dir="$(mktemp -d)"

cleanup() {
    rm -rf "$stage_dir"
}
trap cleanup EXIT

cp "$repo_dir/__init__.py" "$stage_dir/__init__.py"
cp "$repo_dir/manifest.json" "$stage_dir/manifest.json"
cp "$repo_dir/cardscheduler/config.json.example" "$stage_dir/config.json"
cp -R "$repo_dir/cardscheduler" "$stage_dir/cardscheduler"

rm -rf "$stage_dir/cardscheduler/tests"
find "$stage_dir" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$stage_dir" -type f \( \
    -name '*.pyc' -o \
    -name '*.pyo' -o \
    -name '.DS_Store' \
\) -delete

mkdir -p "$target_dir"
rsync -a --delete "$stage_dir/cardscheduler/" "$target_dir/cardscheduler/"
install -m 644 "$stage_dir/__init__.py" "$target_dir/__init__.py"
install -m 644 "$stage_dir/manifest.json" "$target_dir/manifest.json"
if [[ ! -f "$target_dir/config.json" ]]; then
    install -m 644 "$stage_dir/config.json" "$target_dir/config.json"
fi

printf 'Synchronized CardScheduler to %s\n' "$target_dir"
printf 'Preserved the installed Anki configuration and user-owned runtime data.\n'
printf 'Fully quit and reopen Anki to load the updated Python modules and menu actions.\n'
