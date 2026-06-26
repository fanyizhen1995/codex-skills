#!/usr/bin/env bash
set -euo pipefail

echo "=== codex-skills environment check ==="
echo "workdir: $(pwd)"

if [ ! -f "README.md" ] || [ ! -d "personal-wiki" ]; then
  echo "error: run this script from the codex-skills repository root" >&2
  exit 1
fi

if [ -f "tasks.json" ]; then
  python3 -m json.tool tasks.json > /dev/null
  echo "tasks.json: valid JSON"
else
  echo "tasks.json: not present yet"
fi

python personal-wiki/tools/wiki_cli/cli.py --root personal-wiki validate > /tmp/codex-skills-wiki-validate.log
echo "personal-wiki validate: ok"

echo "Optional deeper checks:"
echo "  cd personal-wiki/apps/crawler_workbench/backend && PYTHONPATH=. pytest -q"
echo "  cd personal-wiki/apps/crawler_workbench/frontend && npm test && npm run build"
echo "  python3 harness-step4-evaluator-gates/scripts/test_step4_skill.py"
echo "=== environment check complete ==="
