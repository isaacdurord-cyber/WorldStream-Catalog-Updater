# WorldStream Cloud Catalog Updater

Runs automatically every day at **08:00 UTC** (03:00 EST / 04:00 EDT), and can also be run manually from **Actions → Refresh WorldStream catalog → Run workflow**. GitHub scheduled jobs may be delayed.

## What it provides
- Movie metadata from Apple's iTunes Search API
- TV series metadata from TVMaze
- `public/catalog.json` containing titles, posters, genres, years and descriptions where available
- No API key and no TV-side configuration

## Important limitation
This is a **metadata-only catalog**. It does not collect Chillflix's inventory, include movie or episode streams, or make titles playable. The feed has `playable: false` and `playback_url: null` for every entry. Do not show a Play button for these titles.

Once the first workflow completes, the JSON will be available at:
https://raw.githubusercontent.com/isaacdurord-cyber/WorldStream-Catalog-Updater/main/public/catalog.json

The Android TV app is **not connected** to this repository yet. The app will need a catalog adapter for this schema and a separately licensed playback provider.

## Troubleshooting
If the workflow cannot push, enable **Settings → Actions → General → Workflow permissions → Read and write permissions** for this repository.
