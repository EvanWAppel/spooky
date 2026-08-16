# Deploying spooky to Railway

The app is a Plotly Dash app served by gunicorn. It reads only committed JSON
(`data/episodes/`) at startup — **no runtime API keys, no database, no network
fetch**. A fresh clone can serve immediately.

`nixpacks.toml` pins the build: uv installs the interpreter from
`.python-version` and runs `uv sync --locked --no-dev`, then starts
`gunicorn app:server --bind 0.0.0.0:$PORT`. This removes the "will the builder
detect uv?" risk — the deploy environment matches CI.

## Owner steps (account-bound — do these once)

1. **Merge to `main`.** Railway deploys from `main`. Open a PR from the current
   working branch and merge it (CLAUDE.md forbids pushing to `main` directly).
2. **Create the Railway service** from the GitHub repo `EvanWAppel/spooky`,
   targeting the `main` branch.
3. **Turn sleep / serverless OFF.** The service must be always-on (PRD §4.1) —
   a cold-start 502 is a v1 acceptance failure (J-08).
4. **Set environment variables** (Railway → Variables):
   - `FLASK_SECRET_KEY` — any stable random string (keeps Flask sessions stable
     across restarts).
   - `WIKI_USER_AGENT` — `spooky/0.1 (appelew@gmail.com)` (optional; used only by
     the build pipeline, not the running app).
   - **Do NOT set** `ANTHROPIC_API_KEY` or `TMDB_API_KEY` — the running app never
     reads them (they belong to the local build/logline steps).
5. **Point the domain.** Add `spooky.evanappel.me` as a custom domain on the
   service and let Railway issue TLS.

## Verify

```sh
curl -sI https://spooky.evanappel.me | head -1        # → HTTP/2 200
curl -s https://spooky.evanappel.me | grep -c "unofficial fan project"   # → ≥1
# Then leave it idle 20 min and repeat — still 200, not 502 (always-on check).
```

Once it's live, drop the URL into the README's **Live demo** line.

## Local smoke test (matches the production command)

```sh
uv run gunicorn app:server --bind 0.0.0.0:8050
curl -s -o /dev/null -w "%{http_code}\n" localhost:8050   # → 200
```
