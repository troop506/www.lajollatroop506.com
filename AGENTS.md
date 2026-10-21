# Working in this repository

Read [README.md](README.md) first. Notes for agents (Claude Code, Codex, …):

## Where things run

| Piece | Where | Account |
|---|---|---|
| Site hosting | GitHub Pages, built by [.github/workflows/pages.yml](.github/workflows/pages.yml) | troop506 GitHub org |
| CMS | Sveltia CMS at `/admin/`, loaded from unpkg (version pinned in [static/admin/index.html](static/admin/index.html)) | — |
| CMS sign-in (OAuth client) | Cloudflare Worker deployed from [troop506/sveltia-cms-auth](https://github.com/troop506/sveltia-cms-auth), a fork of `sveltia/sveltia-cms-auth` | Cloudflare account **eric@busboom.org** (signs in with Google) |
| GitHub OAuth App the worker uses | troop506 org → Settings → Developer settings → OAuth Apps | troop506 GitHub org |

The worker holds `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` and
`ALLOWED_DOMAINS`; its URL (https://sveltia-cms-auth.holy-snow-2c62.workers.dev) is `backend.base_url` in
[static/admin/config.yml](static/admin/config.yml). If sign-in breaks, check
the worker's variables and that the OAuth App's callback URL is
`<worker URL>/callback`.

## Rules

- Content edits from the CMS land as commits on `master`; pull before editing
  content by hand.
- Keep the WordPress look: templates in `layouts/` print the old theme's
  markup so the CSS in `static/wp-content/` applies unchanged. Don't restyle.
- `migration/` was a one-time conversion; re-running `wp2hugo.py` overwrites
  `content/`, so don't run it now that people edit in the CMS.
- Never commit `.env` or the OAuth client secret.
