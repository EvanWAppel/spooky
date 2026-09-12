# BLOCKED — what I need from Evan

- [ ] 🔴 **`ANTHROPIC_API_KEY` for logline drafting (group F)** — set in local `.env` (and as a GitHub Actions secret if refresh runs). Free tier, not a spend risk. Request at https://console.anthropic.com/account/keys.
- [ ] 🔴 **Railway always-on deploy (C-19 / I-01 / I-02)** — create a Railway service from `EvanWAppel/spooky` targeting `main`; disable sleep/serverless (a cold-start 502 is an acceptance failure per PRD §4.1). Set `FLASK_SECRET_KEY` (stable random) + `WIKI_USER_AGENT` (`spooky/0.1 (appelew@gmail.com)`). Point `spooky.evanappel.me` at the service with TLS. Verify: `curl https://spooky.evanappel.me` returns 200 and stays 200 after 20 min idle.
- [ ] 🔴 **Human logline review (F-07)** — review all 220 AI-drafted loglines through `tools/review.py`; approve/edit/reject each. Blocks J-05 and live deployment.
- [ ] 🟡 **Episode classification spot-check (G-06)** — verify classification decisions against Fox DVD volumes; adjudicate contested episodes into `data/overrides/` where you disagree with the voting outcome.
- [ ] 🟡 **Recruiter usability test (J-09)** — show the live site to someone unfamiliar with *The X-Files*; record what they say it does in 10 seconds. Note in `POSTMORTEM.md`.
