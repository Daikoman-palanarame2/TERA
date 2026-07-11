# TERA Pre-Flight Release & Deployment Checklist

Use this checklist to verify repository integrity and correctness before deploying to Render or packaging public Docker container releases.

---

## 1. Secrets and Credentials Audit
- [ ] **No Hardcoded Keys:** Run a search across all files to ensure no API keys (e.g. `fw_` keys) are present.
- [ ] **Environment Configuration:** Confirm `.env.example` contains placeholders only.
- [ ] **Git History Clean:** Check that `.env` files are in `.gitignore` and have never been committed.

---

## 2. Docker Configuration
- [ ] **Platform Target:** The Dockerfile specifies `--platform=linux/amd64` to avoid architecture mismatches.
- [ ] **Multi-stage Integrity:** Frontend Next.js build (`frontend-builder` stage) compiles successfully before python setup.
- [ ] **Dynamic Port Binding:** Container binds port dynamically via the `$PORT` environment variable injected by Render (falling back to `7860` if unset).
- [ ] **Conditional Static Mount:** Backend `app/main.py` starts up successfully even if static UI assets are absent.

---

## 3. Entrypoint and CLI Compatibility
- [ ] **No Args Default:** Launching `/app/entrypoint.sh` with no arguments starts the web server (`uvicorn app.main:app`).
- [ ] **Web Arg Support:** Launching `/app/entrypoint.sh web` starts the web server.
- [ ] **CLI Batch Backwards Compatibility:** Running `/app/entrypoint.sh /input/tasks.json /output/results.json` triggers `run_batch.py` exactly as before.
- [ ] **Self-Test Mode:** Running `/app/entrypoint.sh --self-test` executes TERA diagnostics and exits.

---

## 4. Local Application Verification
- [ ] **All 64 Unit Tests Pass:**
  ```bash
  python -m unittest discover tests
  ```
- [ ] **Health & Readiness Endpoints:**
  - GET `/health` returns `{"status": "ok"}`
  - GET `/ready` returns `{"status": "ok"}`
- [ ] **UI Presentation Layer Decoupling:** The UI requests data from the backend `/api/router-inspector` and computes no routing, cost, or utility decisions on the client side.
- [ ] **Savings Transparency:** Backend returns dense baseline cost, TERA actual cost, cost savings, and token savings. The UI renders them.
- [ ] **Mock Adapter Mode:** App functions in mock offline mode when no API keys are present.

---

## 5. Render Live Public Deployment Smoke Test
- [ ] **HTTPS Deployment URL:** The web service dashboard loads correctly over HTTPS.
- [ ] **Health Probe:** `GET https://<your-service>.onrender.com/health` returns `{"status": "ok"}`
- [ ] **Readiness Probe:** `GET https://<your-service>.onrender.com/ready` returns `{"status": "ok"}`
- [ ] **Cold Start Tolerance:** Opening the app after 15 minutes of inactivity successfully triggers container wake-up within 50-90s, and pages load successfully without console failures.
- [ ] **Prompt Verification:** Submitting a query like `What is 2 + 2?` successfully executes routing decisions, retrieves Fireworks API token counts and latencies, and renders the backend-computed savings percentages.
