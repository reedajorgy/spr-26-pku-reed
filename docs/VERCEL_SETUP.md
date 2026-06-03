# Vercel setup (read this if you get 404 NOT_FOUND)

Local `uvicorn` works because **you** start Python. Vercel only runs Python if the build **creates a serverless function**. If the build finishes in ~1 second with no Python step, you get **404 on every URL** (including `/api/index`).

## Check your Vercel project settings

In [Vercel Dashboard](https://vercel.com) → your project → **Settings** → **General** → **Build & Development Settings**:

| Setting | Correct value | Wrong value (causes 404) |
|--------|----------------|---------------------------|
| **Root Directory** | *(empty)* or `.` | A subfolder that does not contain `api/index.py` |
| **Framework Preset** | **Other** | N/A (Other is fine with `vercel.json` `builds`) |
| **Build Command** | **empty** (Override **off**) | `npm run build`, `next build`, etc. |
| **Output Directory** | **empty** (Override **off**) | `public`, `dist`, `.next`, `build` |
| **Install Command** | **empty** (use `vercel.json`) or match repo | Something that skips Python |

**Output Directory is the #1 misclick.** If Vercel looks for static files in `public/` and there is no app there, every request returns `NOT_FOUND`.

## What this repo uses

- `vercel.json` **`version": 2`** + **`builds`** `@vercel/python` on `api/index.py` — forces one Python function to be built.
- **`routes`** send all paths to `api/index.py` (not `/app.py` — that would download source).
- `installCommand` vendors deps into `python_deps/`; `api/index.py` adds that to `sys.path`.

## After pushing

1. **Deployments** → **Redeploy** → enable **Clear build cache**.
2. Open the new deployment’s **Build** log. You should see **`@vercel/python`** / `api/index.py`, not only `Build Completed in /vercel/output [14ms]`.
3. Test:
   - `https://YOUR-URL/api/deploy-check` → JSON (not 404)
   - `https://YOUR-URL/` → study UI

## Still 404?

Paste from the latest deployment:

- Build log (full)
- Screenshot of **Build & Development Settings**
- Result of `curl -I https://YOUR-URL/api/index`
