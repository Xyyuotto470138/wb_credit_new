#!/bin/sh
# Capture the enhancement screens on the saved live case without leaving it changed.
# The saved case only runs from its own folder, so it is backed up, used in place and put back.
#   scripts/screens/enhancements.sh [blocks,sense,papers,review,update] [--live]
#   --live allows live model calls (costs money; logged in the cost ledger): the sense check, and the update proposals.
#   update is not in the default list: it redrafts every affected section through the live model.
#   KEEP_AFTER=path keeps a copy of the case as the run left it (it only runs again from runtime/demo_live/case).
set -e
cd "$(dirname "$0")/../.."
CASE=runtime/demo_live/case; BACKUP=runtime/demo_live/case_before_screens
[ -d "$BACKUP" ] && { rm -rf "$CASE"; mv "$BACKUP" "$CASE"; }   # a run that was stopped part-way
[ -d "$CASE" ] || { echo "No saved live case."; exit 1; }
cp -R "$CASE" "$BACKUP"
LIVE=; [ "$2" = "--live" ] && LIVE=--live
scripts/demo/serve.sh --keppel $LIVE > runtime/enhancement_screens.log 2>&1 &
SERVER=$!
restore() { set +e; kill $SERVER 2>/dev/null; pkill -P $SERVER 2>/dev/null; sleep 1; [ -n "$KEEP_AFTER" ] && { rm -rf "$KEEP_AFTER"; cp -R "$CASE" "$KEEP_AFTER"; }; rm -rf "$CASE"; mv "$BACKUP" "$CASE"; }
trap restore EXIT INT TERM
until curl -s -o /dev/null http://127.0.0.1:15300; do sleep 0.5; done
node scripts/screens/capture_enhancements.mjs http://127.0.0.1:15300 "${1:-blocks,sense,papers,review}"
