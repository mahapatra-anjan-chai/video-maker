#!/usr/bin/env bash
# Run every skill's tests: each .claude/skills/<name>/scripts/tests/ package, from its scripts/ folder.
# New skills are found on their own, so a contributed skill's tests always run (npm test, setup.sh, GitHub).
#
#   bash tests.sh            all skills; the last line says OK or FAILED
#   bash tests.sh -q         one line per skill, no test output
set -u
cd "$(dirname "$0")"
QUIET=0; [ "${1:-}" = "-q" ] && QUIET=1
PY="$(command -v python3)"
PASS=0; FAIL=0; FAILED=()
for t in .claude/skills/*/scripts/tests; do
  [ -f "$t/__init__.py" ] || continue
  skill="$(basename "$(dirname "$(dirname "$t")")")"
  if [ "$QUIET" = 1 ]; then
    ( cd "$(dirname "$t")" && "$PY" -m unittest tests >/dev/null 2>&1 )
  else
    echo "== $skill"
    ( cd "$(dirname "$t")" && "$PY" -m unittest tests )
  fi
  if [ $? = 0 ]; then PASS=$((PASS + 1)); [ "$QUIET" = 1 ] && echo "  ✓ $skill"
  else FAIL=$((FAIL + 1)); FAILED+=("$skill"); [ "$QUIET" = 1 ] && echo "  ✗ $skill"; fi
done
echo
if [ "$FAIL" = 0 ] && [ "$PASS" -gt 0 ]; then echo "$PASS skills tested: OK"
else echo "$FAIL of $((PASS + FAIL)) skills failed (${FAILED[*]-none found}): FAILED"; exit 1; fi
