#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
archive_path="$repo_dir/card-scheduler.ankiaddon"
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

rm -f "$archive_path"
(
    cd "$stage_dir"
    find . -type f -print0 | LC_ALL=C sort -z | xargs -0 zip -X -q "$archive_path"
)

printf '%s\n' "$archive_path"
