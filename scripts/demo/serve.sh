#!/bin/sh
# Run the WB Credit mock demo (mock provider, synthetic data, no live calls).
#   scripts/demo/serve.sh                 this laptop only: http://127.0.0.1:15300
#   scripts/demo/serve.sh --phone         on this Mac's Tailscale address only (tailnet devices, no public tunnel)
#   add --prepared                        start with files loaded and 11 sections drafted (mock case only)
#   add --fresh                           discard the saved demo case and start again (mock case only)
#   add --keppel                          open the new-to-bank Keppel REIT case saved by scripts/demo/live_run.py,
#                                         with the ESR-REIT renewal (mock drafts) as a second paper.
#                                         Its drafts were made with the live model; viewing them makes no model calls.
#   add --live                            with --keppel: allow live model calls from the screens (drafting costs money)
# Stop with Ctrl+C. The back end always listens on 127.0.0.1 only.
set -e
cd "$(dirname "$0")/../.."
HOST=127.0.0.1; PREPARED=; FRESH=; KEPPEL=; LIVE=; MORE=
for arg in "$@"; do
  case "$arg" in
    --phone) HOST=$(tailscale ip -4 | head -1); [ -n "$HOST" ] || { echo "Tailscale is not connected on this Mac."; exit 1; } ;;
    --prepared) PREPARED=1 ;;
    --fresh) FRESH=1 ;;
    --keppel) KEPPEL=1 ;;
    --live) LIVE=1 ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done
CASE=runtime/demo_phone/case; PACK=demo/synthetic
if [ -n "$KEPPEL" ]; then
  CASE=runtime/demo_live/case; PACK=demo/synthetic_keppel; PREPARED=; FRESH=
  [ -d "$CASE" ] || { echo "No saved live case. Run: .venv/bin/python scripts/demo/live_run.py"; exit 1; }
  [ -n "$LIVE" ] && export WB_CREDIT_LIVE=1
  MORE=demo/synthetic   # a second paper (the ESR-REIT renewal, mock drafts) so the papers list can switch between papers
fi
[ -n "$FRESH" ] && rm -rf "$CASE"
export LLM_PROVIDER=mock PYTHONDONTWRITEBYTECODE=1 DEMO_HOST="$HOST" DEMO_PORT=15300 DEMO_API_PORT=18200
(cd frontend && npm run build >/dev/null)
.venv/bin/python -c 'import sys, uvicorn; from backend.app.local import create_demo_app; uvicorn.run(create_demo_app(sys.argv[1], sys.argv[2], sys.argv[3:]), host="127.0.0.1", port=18200, log_level="warning")' "$CASE" "$PACK" $MORE &
API=$!
trap 'kill $API $WEB 2>/dev/null' EXIT INT TERM
until curl -s -o /dev/null http://127.0.0.1:18200/health; do sleep 0.5; done
[ -n "$PREPARED" ] && .venv/bin/python scripts/demo/prepare_case.py http://127.0.0.1:18200
[ -n "$MORE" ] && .venv/bin/python scripts/demo/prepare_case.py http://127.0.0.1:18200 ESR-REIT >/dev/null
(cd frontend && exec node node_modules/vite/bin/vite.js preview --config ../scripts/demo/vite.demo.config.mjs) &
WEB=$!
echo "WB Credit demo: http://$HOST:15300   (Ctrl+C to stop)"
wait $WEB
