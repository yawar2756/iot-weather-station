# Changes in this version

Everything below was verified: backend against a real PostgreSQL (56 checks) and the dashboard
logic in a DOM (25 checks). The firmware was **not** compiled or flashed (no ESP toolchain here):
build it in the Arduino IDE and watch the serial monitor on first run.

## Bugs fixed
| # | Problem | Fix |
|---|---|---|
| 1 | Service worker served pages and `/api/export` cache-first, so old UI and the first CSV stuck forever | Pages and API are network-first, export is never cached, cache version bumped (`v3`) |
| 2 | `value \|\| '--'` hid real 0 readings (0 °C, 0 %, 0 km/h), also `if stats[0]` in Python | Null-safe formatting in JS, `is not None` in Python |
| 3 | `-1` doubled as "sensor failed" and as a real -1 °C reading | Missing data is `NULL` everywhere. Old `-1` rows are cleaned on startup |
| 4 | `-1 km/h` and `-1 %` shown in the UI | Negative wind / humidity / light is treated as missing |
| 5 | Calm wind sent as `-1` ("not connected") | Calm = `0`. Sensors that are not fitted send `null` (`HAS_*` flags) |
| 6 | Wind = clicks x 2.4 over a 12 s window (about 12x too high for a 2.4 km/h per Hz sensor) | Clicks / real elapsed seconds x `WIND_KMH_PER_HZ`, with debounce and atomic read |
| 7 | LDR "visibility" triggered "Low Visibility" every night | Renamed "Light Level"; alert is opt-in (`VISIBILITY_ALERT_ENABLED=1`) |
| 8 | API error or "no data" JSON displayed as "Live / Operational" | Anything without a valid `device_status` shows "Unavailable" |
| 9 | Offline wiped all values | Last known values stay, dimmed, with a real "last update" age |
| 10 | Export averaged the `-1` sentinels and picked rain alphabetically | `NULL`-aware `AVG`, real rain wins over "No Rain" |
| 11 | DB connections leaked on errors, no index, unlimited growth | `with db_cursor()` always closes; index on `created_at`; `RETENTION_DAYS` pruning |
| 12 | `/api/seed` always live, key in the URL, shared with the device | Off unless `ENABLE_SEED=1`, header-only key, DEMO badge on the dashboard |
| 13 | Firmware: WiFi loop could hang forever, no recovery | 30 s WiFi timeout, auto-restart after 10 failed posts, 20 s HTTP timeout |
| 14 | Fingerprint comment said SHA-256 (it is SHA-1) and cert renewal silently kills the ESP | Comment fixed, clear log message, regeneration command documented |

## Smaller fixes
- `--radius-full` defined (pills were square); 1.7 MB `favicon.png` replaced by 128/192/512 px icons
- Chart.js pinned to 4.4.7; `requirements.txt` ranges; `Procfile` uses `$PORT`
- Footer year is dynamic; CORS limited to read-only GET endpoints; constant-time API-key compare
- CSV export guards against spreadsheet formula injection
- Inline CSS/JS moved to `static/css` and `static/js`
- Accessibility: skip link, `aria-live` status, `role="alert"`, `aria-hidden` icons, chart label, one `<h1>` per page
- Open Graph / Twitter tags, canonical link on every page
- README: honest sensor limits, DHT11 range warning, curl-based demo seeding, env var table
- `.claude/` removed and git-ignored

## Still on you
1. **Replace the DHT11** (0-50 °C only) with a DHT22 or BME280 before winter; change `DHTTYPE`.
2. **Check `WIND_KMH_PER_HZ`** against your anemometer datasheet.
3. **Regenerate `SERVER_FINGERPRINT`** whenever the host certificate renews (command in the `.ino`).
4. Add an uptime monitor on `/ping` so Render's free tier does not cold-start on visitors.
5. After deploying, unregister the old service worker once (DevTools > Application > Service Workers > Unregister) or hard refresh.
