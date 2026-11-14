#!/bin/sh
# Offline test runner. Always the mock provider, never the network.
#   scripts/run_tests.sh          normal run: parallel, without the tests marked slow
#   scripts/run_tests.sh --all    every test, parallel. Run before a UI block counts as done.
#   scripts/run_tests.sh --gate   every test, one process, slowest tests listed. Run at gates and the freeze.
# Extra arguments go to pytest, for example: scripts/run_tests.sh tests/test_intake.py -k dedup
# TEST_WORKERS sets the number of parallel workers (default: one per core).
set -e
cd "$(dirname "$0")/.."
export LLM_PROVIDER=mock PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1
run() { exec .venv/bin/python -m pytest -q -p no:cacheprovider "$@"; }
parallel="-p xdist -n ${TEST_WORKERS:-auto} --dist worksteal --basetemp=runtime/pytest-parallel"
case "$1" in
  --gate) shift; run --basetemp=runtime/pytest-gate --durations=25 "$@" ;;
  --all)  shift; run $parallel "$@" ;;
  *)      run $parallel -m "not slow" "$@" ;;
esac
