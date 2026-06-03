# Vercel setup (404 NOT_FOUND)

## That log you pasted

`GET / → 404`, **Middleware**, ~43ms, deployment `dpl_4eZYsZQtCy7Zkhh1vzHdHYaXUD1C` means **no Python app was running** on that deployment. It is not a bug in your study UI code.

**Check the deployment’s commit** in the Vercel UI. If it is not the latest `main` with `main.py` at the repo root, you are still looking at an old broken deploy.

## Why local works

`./run_flashcards_web.sh` starts **uvicorn** on your machine. Vercel only runs what the **build** produces. If the build never creates a FastAPI function, every URL returns `NOT_FOUND`.

## Dashboard settings (do this in the UI)

[Vercel Dashboard](https://vercel.com) → project → **Settings** → **General** → **Build & Development Settings**

| Setting | Required |
|--------|----------|
| **Root Directory** | Empty (repository root) |
| **Framework Preset** | **FastAPI** (not “Other”) |
| **Build Command** | Override **OFF** (empty) |
| **Output Directory** | Override **OFF** (empty) — **never** `public` or `dist` |
| **Install Command** | Override **OFF** (use repo `vercel.json`) |

**Output Directory** set to `public` is the most common cause of sitewide 404.

After changing Framework to **FastAPI**, redeploy with **Clear build cache**.

## How this repo deploys

- Root **`main.py`** exports `app` (handles `/`, `/api/deploy-check`, `/static/`, etc.).
- **`pyproject.toml`**: `[tool.vercel] entrypoint = "main:app"`.
- **`vercel.json`**: only `installCommand` (vendors deps into `python_deps/`) and `PYTHONPATH=.`.
- **Do not** use `rewrites` to `*.py` paths (downloads source).
- **Do not** use legacy `builds` / `functions.api/index.py` (conflicts with modern FastAPI builds).

## Verify after deploy

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://YOUR-PROJECT.vercel.app/api/deploy-check
```

- **200** + JSON → working.
- **404** → build still did not produce a Python function; send the **full build log** and a screenshot of Build settings.
