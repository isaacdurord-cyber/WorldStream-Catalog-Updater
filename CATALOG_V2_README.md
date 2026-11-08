# WorldStream catalog and streaming reliability

The updater now targets **up to 10,000 highly ranked films and 10,000 series listings**.
These are **metadata**, not playable films or episodes. Never label titles playable unless an
authorized direct video source is available.

## Data sources
- **TVmaze**: public show index, sorted by service weight/rating. A daily run scans older and newly published pages. Fetch failures preserve previous output.
- **Movies**: optional TMDB API read token set only in GitHub **Settings > Secrets and variables > Actions** as `TMDB_READ_TOKEN`. The token is not in the Android app. Without it, a best-effort Wikidata metadata query runs; it can be rate-limited, so 10k movies is not guaranteed.
- **providers.json**: operator-authorized direct MP4/HLS/DASH/WebM videos. Current entries are only diagnostic test videos.
- **Wikimedia Commons** and Mozilla examples: `public/diagnostics.json`, separated from the main Movies list.
- **public/discovery_report.json**: reports website reachability and any verified integration document. It does **not** extract third-party movie streams or authorize redistribution.

## Fire TV
1. Install the **v1.6 stability project** in Android Studio.
2. Test a Live TV channel on both emulator and Fire TV Stick.
3. While playing press **MENU** > **Playback diagnostics**.
4. Compare **Audio underruns**, **Dropped video frames**, and **Rebuffer events**.
5. Use Android Studio Logcat: `WorldStreamPlayback` or `FATAL EXCEPTION`.

Emulator audio glitches may be caused by virtualization, but this must be verified on the device.
A source being accessible over HTTP is **not** sufficient evidence that its codecs will play.
The app cannot infer commercial-movie playback URLs from FMHY bookmarks alone.
