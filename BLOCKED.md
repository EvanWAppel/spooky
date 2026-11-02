# BLOCKED — what I need from Evan

> **Fleet repo (_system D-036, D-051, D-052):** spooky's blockers live in Jira as *Needs Evan*
> tickets (component `spooky`; file with `uv run --project ~/Documents/_system sys file-blocker`);
> `sys blockers` mirrors them into the todo dashboard. Two kinds stay here: `[sec]` blockers (the
> security dashboard counts them only here) and anything Jira must not hold — rosters, secrets,
> unpublished writing. Moved 2026-11-01: EA-199, EA-200, EA-201, EA-202, EA-203, EA-204.

- [ ] 🔴 [sec] **`ANTHROPIC_API_KEY` for logline drafting (group F)** — set in local `.env` (and as a GitHub Actions secret if refresh runs). Use a scoped key from a dedicated, spend-capped workspace, not your personal key (see the `project.toml` `[keys]` item below); mint it at https://console.anthropic.com/settings/workspaces.
- [ ] 🟡 [sec] **Branch protection on `main` (public repo)** — `gh api repos/EvanWAppel/spooky/branches/main/protection` returns 404 "Branch not protected" (checked 2026-10-22). Railway deploys from `main`, so an unprotected `main` means one stray push is a deploy. Run the standard command from your global CLAUDE.md, with `<repo>` = `spooky` and `<default-branch>` = `main` (PR required, 0 approvals, dismiss stale reviews, no force-push or delete, `enforce_admins: false`). Or tell a session "apply branch protection to spooky" and it will.
- [ ] 🟡 [sec] **Anthropic key facts for `project.toml` `[keys]`** — `project.toml` lists `paid = ["anthropic"]` (local logline/triage steps only; the deployed app reads no key) with `isolated`/`spend_cap` = `unknown`. Tell me whether the `ANTHROPIC_API_KEY` in your local spooky `.env` comes from a dedicated workspace with a spend cap. I'll set both to `yes`/`no`; if it's your personal key, mint a scoped key in a capped workspace at https://console.anthropic.com/settings/workspaces before the next logline or T-06 run. While you're there, check the `project.toml` draft and say "verify it" so a session flips `verified = true`.
