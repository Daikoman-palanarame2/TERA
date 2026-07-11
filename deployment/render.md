# Deploying TERA on Render

This guide provides step-by-step, beginner-friendly instructions to deploy the TERA (Token-Efficient Routing Agent) application as a public interactive web service on Render's free tier.

---

## 1. Render Free Tier Cold-Start Behavior

> [!IMPORTANT]
> **Free Tier Spin-Down:** Render's Free tier automatically spins down (sleeps) web service containers after **15 minutes** of inactivity.
> 
> **Cold Start Wake-up:** When a judge first opens the application URL after it has gone idle, Render will boot a fresh instance. This cold start typically takes **50 to 90 seconds**. The browser will show a loading spinner or delay during this window. Subsequent requests are executed in standard real-time scales (< 0.2ms routing, ~1.5s API latency).

---

## 2. Prerequisites

Before starting, ensure you have:
1. A **GitHub account** where your TERA repository is hosted.
2. A **Render account** (Sign up for free at [render.com](https://render.com)).
3. A valid **Fireworks AI API Key** (Get yours from [fireworks.ai](https://fireworks.ai/)).

---

## 3. Option A: Blueprint 1-Click Deployment (Recommended)

TERA includes a `render.yaml` Blueprint template that automatically configures the web service, ports, build environment, and health check routes.

1. **Log in** to your Render dashboard.
2. Click on the **Blueprints** tab in the top navigation bar, then click **New Blueprint Instance**.
3. Connect your GitHub repository containing the TERA code.
4. Render will read the root `render.yaml` and prompt you for values:
   - **Service Name:** `TERA-router-inspector` (default)
   - **FIREWORKS_API_KEY:** *Enter your actual Fireworks AI API key (e.g., `fw_...`)*
   - **FIREWORKS_BASE_URL:** `https://api.fireworks.ai/inference/v1` (pre-filled)
   - **ALLOWED_MODELS:** `accounts/fireworks/models/deepseek-v4-pro,accounts/fireworks/models/gpt-oss-120b` (pre-filled)
   - **MAX_CONCURRENCY:** `4` (pre-filled)
5. Click **Approve** at the bottom of the page.
6. Render will automatically configure and launch the multi-stage Docker build.

---

## 4. Option B: Manual Web Service Setup

If you prefer to configure the deployment manually:

1. In the Render Dashboard, click the **New +** button and select **Web Service**.
2. Connect your GitHub repository.
3. Configure the service parameters:
   - **Name:** `tera-router-inspector`
   - **Environment:** Select **Docker** (Crucial! Do not select Python or Node).
   - **Branch:** `main`
   - **Region:** Choose the region closest to you (e.g., `Oregon (US West)`).
   - **Plan:** Select **Free**.
4. Click **Advanced** and scroll to **Environment Variables**:
   - Add Key: `FIREWORKS_API_KEY`, Value: *your API key*
   - Add Key: `FIREWORKS_BASE_URL`, Value: `https://api.fireworks.ai/inference/v1`
   - Add Key: `ALLOWED_MODELS`, Value: `accounts/fireworks/models/deepseek-v4-pro,accounts/fireworks/models/gpt-oss-120b`
   - Add Key: `MAX_CONCURRENCY`, Value: `4`
5. Scroll down to **Health Check Path** and set it to: `/health` (This lets Render verify that the FastAPI server has initialized).
6. Click **Create Web Service**.

---

## 5. Build & Startup Logs

1. The service dashboard will show **Building**.
2. Click on **Logs** in the left navigation sidebar to watch progress.
3. The build process executes the multi-stage build:
   - Node compiles the Next.js static website to `frontend/out`.
   - Python copies the assets, builds packages, and executes the uvicorn web server.
4. **Expected Startup Output:**
   ```
   ====================================
   TERA Track 1 Production Startup
   ====================================
   Launching TERA Web Server on port 10000...
   INFO:     Started server process [1]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:10000 (Press CTRL+C to quit)
   ```
   *(Note: Render dynamically assigns a port via the `$PORT` environment variable. Our entrypoint parses this automatically).*
5. Once Uvicorn starts and `/health` responds with `{"status": "ok"}`, Render will mark the service as **Live** and print a public HTTPS URL (e.g., `https://tera-router-inspector.onrender.com`).

---

## 6. Troubleshooting & Updates

- **Automatic Deployments:** Render automatically redeploys your web application every time you push a new commit to your GitHub `main` branch.
- **Viewing Health Status:** Query the health endpoints directly over HTTPS:
  - `GET https://<your-service>.onrender.com/health` (Returns `{"status": "ok"}`)
  - `GET https://<your-service>.onrender.com/ready` (Returns `{"status": "ok"}`)
- **Build Failures:** Check the Render Logs. Ensure the root `Dockerfile` and `entrypoint.sh` are present and that Node/Python versions match configurations.
