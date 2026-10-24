#!/usr/bin/env bash
# Start Saathi on http://localhost:8010
#   ./run.sh            start the server
#   ./run.sh test       run the tests
#   ./run.sh sample     regenerate the sample form and a filled example in data/outbox/
set -euo pipefail
cd "$(dirname "$0")"
unset PYTHONPATH   # keep system-wide packages (e.g. ROS) out of the app

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi

case "${1:-serve}" in
  test)   .venv/bin/python -m pytest -q "${@:2}" ;;
  sample) .venv/bin/python scripts/make_sample_form.py && .venv/bin/python scripts/fill_sample.py ;;
  serve)  exec .venv/bin/uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8010}" --reload ;;
  *)      echo "usage: ./run.sh [serve|test|sample]"; exit 1 ;;
esac
