#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/../.." && pwd)"
output="$project_root/lambda/deployment.zip"

rm -f "$output"
(
  cd "$script_dir"
  zip -q "$output" parse_cloudtrail.py
)

unzip -t "$output" >/dev/null
unzip -l "$output" | grep -qE '[[:space:]]parse_cloudtrail\.py$'
printf 'Created validated Lambda deployment package: %s\n' "$output"
