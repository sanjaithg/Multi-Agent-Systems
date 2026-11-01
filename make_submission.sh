#!/usr/bin/env bash
# Build the Moodle zip. Run after generating answers_public.json and traces/ with real LLM runs.
set -euo pipefail
cd "$(dirname "$0")"
NAME="${1:-submission}"
missing=0
for f in answers_public.json traces report/REPORT.md README.md; do
  [ -e "$f" ] || { echo "MISSING: $f"; missing=1; }
done
grep -q "<Fill in\|<At least" report/REPORT.md 2>/dev/null && { echo "report/REPORT.md still has placeholders"; missing=1; }
[ "$missing" = 0 ] || exit 1
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
rm -f "$NAME.zip"
zip -r "$NAME.zip" README.md requirements.txt .env.example run_queries.py evaluate.py orchestrator graphkit data \
  infra_tools registry curation/curate.py curation/checks.py curation/REPORT.md curation/report.json queries tests \
  template pytest.ini answers_public.json traces report -x '*/__pycache__/*' '*.pyc' '*/.pytest_cache/*' '*/.env'
echo "Created $NAME.zip"
