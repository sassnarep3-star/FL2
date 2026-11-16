#!/bin/sh
# Rebuild every Line Lab artefact in dependency order. Deterministic; no network.
set -e
cd "$(dirname "$0")/../.."
python3 engine/linelab/price_store.py
python3 engine/linelab/model.py
python3 engine/linelab/scoring.py
python3 engine/linelab/availability.py
python3 engine/linelab/depth_graph.py
python3 engine/linelab/backtest.py
python3 engine/linelab/requirements.py
python3 engine/linelab/build_site.py
python3 engine/linelab/check_site.py
