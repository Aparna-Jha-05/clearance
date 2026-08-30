# Deploy: console on Vercel, gateway on a Python host

The console (Next.js) goes on **Vercel**. The gateway (FastAPI) cannot run on
Vercel — it needs a real process and a writable filesystem for the ledger — so it
goes on a **Python host** (Render is used below; Railway / Fly.io work the same
way). Deploy the backend first so you have its URL for the frontend build.

---

## 1. Backend → Render (free)

The repo already contains [`render.yaml`](render.yaml), a [`Procfile`](Procfile),
and [`runtime.txt`](runtime.txt).

1. Push this repo to GitHub (already done).
2. Go to **render.com → New → Blueprint**, connect the repo. Render reads
   `render.yaml` and creates a web service `clearance-gateway`.
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn clearance.app:app --host 0.0.0.0 --port $PORT`
   - Env: `CLEARANCE_OFFLINE=1` (runs on committed corpus + fixtures, no keys)
   - Health check: `/health`
3. Deploy. Note the URL, e.g. `https://clearance-gateway.onrender.com`.
   - Visit `/health` — you should see `{"ok": true, ...}`.
   - The ledger seeds itself on boot, so `/api/ledger` returns rows immediately.

> Free tier sleeps when idle and cold-starts in ~30s; the first console request
> after a sleep may lag, then works. State is ephemeral (it re-seeds on restart),
> which is exactly right for a demo.

_No blueprint?_ Create a **Web Service** manually with the same build/start
commands and the `CLEARANCE_OFFLINE=1` env var. Railway: it reads the `Procfile`
automatically — just add the env var.

---

## 2. Frontend → Vercel

1. **vercel.com → Add New → Project**, import the repo.
2. **Root Directory: `console`** (important — the Next app lives in `console/`,
   not the repo root). Framework preset auto-detects as **Next.js**.
3. **Environment Variables** — add before the first build (Next inlines
   `NEXT_PUBLIC_*` at build time):

   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | `https://clearance-gateway.onrender.com` |

   (your backend URL from step 1, **no trailing slash**)
4. Deploy. Open the Vercel URL → the **Live / Tuning / Ledger** pages load and
   talk to the backend.

If you change `NEXT_PUBLIC_API_BASE` later, **redeploy** so the new value is baked
into the build.

---

## 3. Verify the deployed demo

- **Live** — the paired-verdict hero renders (annotate vs escalate) and the
  decision feed fills in.
- **Tuning** — drag a slider; metrics recompute against the backend in < 300ms.
- **Ledger** — *verify chain* is green; *tamper a row* turns it red.

If a page shows "NEXT_PUBLIC_API_BASE is not set" or a fetch error, the env var is
missing or the backend is asleep/misconfigured — re-check step 1's `/health` and
step 2's env var, then redeploy the Vercel project.

---

## Note on the "backend can't be Vercel" point (for the pitch)

This split is not a limitation of the design — it is the design. CLEARANCE is a
**stateful decision gateway** with an append-only, hash-chained ledger. That is a
process with durable state, not an edge function. Hosting it on a real backend and
the dashboard on the edge is the correct topology, and it is why the ledger's
integrity guarantees mean something.
