#!/usr/bin/env bash
# Snapshot the local demo world into the committed dirs the Docker image ships:
#   backend/.cognee  -> backend/demo_graph  (kuzu graph + lancedb vectors)
#   backend/.cache   -> backend/demo_seed   (corpus, analytics, caches)
# Run AFTER a full local rebuild + warmup:
#   python -m memory_shield.corpus && python -m memory_shield.ingest --fresh
#   (then hit /suggest, /backtest, /track once locally to warm caches)
set -euo pipefail
cd "$(dirname "$0")/../backend"

[ -d .cognee/system ] || { echo "no .cognee store — run ingest first" >&2; exit 1; }
[ -f .cache/corpus.json ] || { echo "no .cache/corpus.json — run corpus first" >&2; exit 1; }

rm -rf demo_graph demo_seed
mkdir -p demo_graph demo_seed

rsync -a .cognee/ demo_graph/

# Everything the serving path reads, minus local-runtime state.
rsync -a .cache/ demo_seed/ \
  --exclude sprout_app.db \
  --exclude telegram_offset.json \
  --exclude 'fallback_*.json' \
  --exclude '__pycache__'

du -sh demo_graph demo_seed
echo "snapshot done — commit backend/demo_graph/ and backend/demo_seed/"
