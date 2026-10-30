# SUSE AI Factory with NVIDIA: interactive demos

Click-through demos of SUSE AI Factory with NVIDIA, recorded on the real product. Open the start page, pick a demo, and click
through it at your own pace. Every demo ends with **Back to all demos**.

**Start page:** https://alessandro-festa.github.io/saif-demos/

Each demo shows the same platform story:

1. **The Blueprint flow**: what the use case is made of, drawn in the Studio.
2. **SUSE AI Factory with NVIDIA**: the Blueprint deployed and at work. The SUSE AI Factory with NVIDIA UI is an extension of
   the Rancher Prime UI, and it can also be consumed via API.
3. **SUSE Security**, where the use case needs it (SecOps, Developer Sandbox).
4. **SUSE Observability**: the Blueprint, the agent's traces and the models.

| Demo | Folder |
|---|---|
| SUSE AI Factory for developers | [`demos/developer-overview`](demos/developer-overview) |
| Factory operations & visual inspection | [`demos/manufacturing`](demos/manufacturing) |
| Fraud detection & investigation | [`demos/finance`](demos/finance) |
| Network configuration & autonomous operations | [`demos/telco`](demos/telco) |
| Conversational shopping assistant | [`demos/retail`](demos/retail) |
| Ambient clinical documentation | [`demos/healthcare`](demos/healthcare) |
| Sovereign agentic SecOps | [`demos/secops`](demos/secops) |
| Traffic incident management | [`demos/traffic`](demos/traffic) |
| Sovereign casework | [`demos/sovereign`](demos/sovereign) |
| Developer Sandbox | [`demos/developer-sandbox`](demos/developer-sandbox) |

A folder appears once its demo is recorded; until then its card on the start page reads *Coming soon*.

## Run it locally

Needs Node.js 20 or newer.

```sh
npm ci
npm run site          # builds dist/: the start page and every demo
npx serve dist        # or any static server; open the printed URL
```

To edit a demo's text, hotspots or blur boxes: `npm run dev` and open the editor at `http://localhost:3000/__demo/editor/`.

## How it is made

The demos are made with the open-source [`interactive-demo`](https://docs.inklyai.dev/open-source/overview) CLI (MIT).
Each demo is a `demo.config.json` plus its `assets/`.

| Path | What it is |
|---|---|
| `catalog.json` | the start page's cards, in order |
| `stories/<slug>.json` | each demo's copy: intro, chapters, the text on every step, blur boxes |
| `scripts/merge-segments.mjs` | joins the captured segments of a demo into `demos/<slug>/` following its story |
| `scripts/site.mjs` | builds `dist/`: every demo, the SUSE branding, the start page |
| `recorder/` | drives the product while `interactive-demo capture` records (needs access to a SUSE AI Factory with NVIDIA installation) |
| `brand/` | SUSE and NVIDIA logos, the SUSE font (SIL OFL 1.1), the SUSE stylesheets |

On every push to `main`, the Pages workflow validates the demos, builds the site and publishes it.
