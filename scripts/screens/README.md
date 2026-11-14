# Screenshot capture (development only)

Playwright is a frontend **devDependency**, authorized in mailbox task 0024. The
capture drives the actual React UI against the saved-pack/mock backend. It creates
an isolated database and logs under `runtime/0024/capture-*`; existing Gate 1 review
work is never reset. Installed Chrome is the default. No model/search calls or
external browser requests are allowed.

From the repository root, with the existing Python and frontend setup:

```sh
node scripts/screens/capture.mjs
node scripts/screens/gallery.mjs
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/screens/verify_pdf.py
```

The commands require permission to launch headless Chrome and bind loopback ports
15124 (Vite) and 18024 (API). They refuse occupied ports rather than replacing an
existing server. Each script closes its browser; capture also terminates both
servers in `finally` and on SIGINT/SIGTERM. Temporary browser profiles stay inside
its repository runtime directory. Use `npm --prefix frontend ci` to install the
locked development dependencies on a fresh machine; keep npm's cache inside the
repository if following the standing local-only filesystem rule.

If installed Chrome is unavailable, install Chromium into ignored repository
storage, then pass the same environment to both commands:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/runtime/ms-playwright" frontend/node_modules/.bin/playwright install chromium
SCREEN_BROWSER=chromium PLAYWRIGHT_BROWSERS_PATH="$PWD/runtime/ms-playwright" node scripts/screens/capture.mjs
SCREEN_BROWSER=chromium PLAYWRIGHT_BROWSERS_PATH="$PWD/runtime/ms-playwright" node scripts/screens/gallery.mjs
```

Outputs are numbered 2880 x 1800 PNGs (1440 x 900 CSS viewport at scale 2), a JSON
capture manifest, the local HTML gallery, and a PDF printed by `page.pdf`. The PDF
uses a 15 x 10 inch page, one screenshot and caption per page. Screens capture
scroll positions in the real long dashboard; they do not composite or restyle the
application. Long panels and PDF pages retain their own scroll behavior. Downloads
are verified and retained only in the ignored run directory.

The flow follows `docs/gate1.md` and `docs/gate2.md`: three tranches, public source
confirmation, saved mock spread, 7/11/14 saved sections, rejected/accepted CA note,
version history, all section editors, Python/source views, draft export, model
comparison, revised valuation and ordered redrafts. Backend assertions verify
fourteen saved sections and the exact 8/9/11/14 Stale chain. Browser errors,
external request attempts and horizontal document overflow fail the run.

Review every PNG and every rendered PDF page before committing a regenerated
pack. Update `docs/screens/README.md` with captions, actual checks and unresolved
layout or coverage limitations. The script's synthetic CA review clicks are
fixture actions, not Sheryl's acceptance or a real credit review.

The verifier uses the project's existing PyMuPDF dependency, checks image sizes,
page count, caption text and image placement, and renders every PDF page under
`runtime/0024/pdf-review/`. Inspect those renders after printing; automated bounds
checks do not replace visual review.

## Live case and enhancement screens (13 Nov 2026)

- `capture_live.mjs`: read-only screens of the saved live case (`docs/screens/live_*.png`). Start `scripts/demo/serve.sh --keppel` first.
- `enhancements.sh [blocks,sense,papers,review] [--live]`: screens of analyst added content, the model sense check, the papers list and the maker and checker flow (`docs/screens/enh_*.png`). These steps change the case, so the script backs the saved case up, runs `capture_enhancements.mjs` and puts the case back, also when it fails. `--live` lets the sense check step call the live model (about USD 0.05, recorded in the cost ledger).
- `enhancements.sh update --live`: the new information scenario on the saved live case (`enh_19` to `enh_29`): loads `demo/synthetic_keppel/late_update/`, then proposes and applies an update for every affected section. Every proposal is a drafting call: about USD 14 for the whole ES. `update_short` does sections 8, 1 and 10 only (about USD 5). `update_look` stops at the What changed page and makes no model call. `KEEP_AFTER=path` keeps a copy of the case as the run left it.
