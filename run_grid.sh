#!/usr/bin/env bash
#
# Run every task five times against both tool setups, for the given models.
# Skips runs whose trace already exists, so it can be stopped and restarted.
#
#   GITHUB_TOKEN=... ./run_grid.sh haiku opus
#
# Traces land in traces/<setup>-<model>/<task>/run-N.jsonl.
# Docker must be running for the "github" setup.

if [ $# -eq 0 ]; then echo "usage: $0 <model> [<model> ...]"; exit 1; fi
: "${GITHUB_TOKEN:?export GITHUB_TOKEN first}"

cd "$(dirname "$0")"

for model in "$@"; do
  for setup in github generated; do      # cheap setup first
    if [ "$setup" = "github" ]; then
      cfg=mcp/github.json; allowed=mcp__github
    else
      cfg=mcp/generated.json; allowed=mcp__github-generated
    fi
    for t in 01 02; do
      dir="traces/$setup-$model/task-$t"
      mkdir -p "$dir"
      for i in 1 2 3 4 5; do
        out="$dir/run-$i.jsonl"
        [ -s "$out" ] && continue
        echo "$(date +%H:%M:%S) $setup / $model / task-$t / run $i"
        claude -p "$(cat tasks/task-$t.md)" \
          --mcp-config "$cfg" --strict-mcp-config \
          --allowedTools "$allowed" --tools "" --model "$model" \
          --output-format stream-json --verbose \
          > "$out" 2> "${out%.jsonl}.stderr"
      done
    done
  done
done
echo "done"
