# WB Credit demo on the phone (Tailscale only)

Mock mode, synthetic demo data, no live model calls. Written 12 Nov 2026.

## Address

**http://100.67.80.15:15300**

Open it in Safari on the iPhone (`iphone-15-pro-max` on the tailnet). The laptop (`s-macbook-pro`) must be awake, on Tailscale, and running the start command below.

## Start, on the laptop

From the project folder:

```sh
scripts/demo/serve.sh --phone --prepared
```

- `--phone` serves the app on this Mac's Tailscale address only. The script reads the address with `tailscale ip -4`, so if Tailscale ever gives the Mac a different address, use the one the script prints.
- `--prepared` loads the files and drafts 11 sections on first start, so the phone opens on a working ES. It takes about 40 seconds. Leave it out to start from an empty case and run the whole flow yourself.
- Add `--fresh` to discard the saved demo case and start again.
- Stop with Ctrl+C. The case is kept in `runtime/demo_phone/` until you use `--fresh`.

To keep the Mac awake while you present, run this in a second terminal: `caffeinate -d`.

## Showing the live Keppel REIT case

```sh
scripts/demo/serve.sh --phone --keppel
```

This opens the new-to-bank case saved by the live run (`scripts/demo/live_run.py`). Viewing it makes no model calls. Add `--live` only if you want the screens to be able to draft with the live model, which costs money.

## What is exposed

- The web app listens on the Tailscale address only (port 15300). It is not on localhost, not on the home or office network address, and there is no public tunnel. Tailscale Serve and Funnel are not configured.
- The back end listens on 127.0.0.1 only (port 18200). The web app passes requests to it.
- Checked on the laptop on 12 Nov 2026: the Tailscale address answered, localhost and the Wi-Fi address refused. It has not been opened from the phone itself; do that once before the meeting. If macOS asks whether `node` may accept incoming connections, choose Allow.

## On the phone

- Sections are the numbered strip under the top bar; swipe it sideways. The coloured dot is the section status.
- The Credit Assistant switch in the top bar opens the chat full screen; the × closes it.
- On the Inputs screen use **Scan folder** (the demo folders are on the laptop). Uploading from the phone works only for files that are on the phone.
- Typed notes for the assistant must not contain figures or dates in mock mode. Figures reach the ES from source files, so that the system computes them.

## Laptop only

```sh
scripts/demo/serve.sh --prepared
```

Then open http://127.0.0.1:15300.

## Files beside this note

- `earlier_mock_case/WB_Credit_demo.mp4`: the first mock demo, kept for reference. 70 second recording of the flow (upload, checklist, draft, open a section, ask the Credit Assistant for a change, accept it, confirm the section, export).
- `earlier_mock_case/WB_Credit_ES_export.pdf` and `.docx`: the ES exported at the end of that recording, on template v0.3.
- Re-record with `node scripts/demo/record_demo.mjs`.

## Product video

`docs/demo/WB_Credit_product_video.mp4` (2 min 2 s, no sound; kept by the project owner, not in this repository, and rebuilt by `scripts/demo/record_product_video.mjs`) is the product video of the live Keppel REIT case. It plays from the phone's Files or Photos app once copied over; it does not need the laptop.
