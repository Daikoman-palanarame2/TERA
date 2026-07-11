# Deploying TERA on Hugging Face Spaces

This guide provides step-by-step, beginner-friendly instructions to deploy the TERA (Token-Efficient Routing Agent) application as a public interactive web service on Hugging Face Spaces.

---

## 1. Prerequisites

Before starting, ensure you have:
1. A **GitHub account** where the TERA repository is hosted.
2. A **Hugging Face account** (Sign up at [huggingface.co](https://huggingface.co/join)).
3. A valid **Fireworks AI API Key** (Get yours from [fireworks.ai](https://fireworks.ai/)).

---

## 2. Setting Up the Space on Hugging Face

1. **Log in** to your Hugging Face account.
2. Click on your profile icon in the top right corner and select **New Space** (or navigate to [huggingface.co/new-space](https://huggingface.co/new-space)).
3. Enter your configuration details:
   - **Space Name:** Choose a name (e.g., `tera-router-inspector`).
   - **License:** Select `mit` or leave blank.
   - **Select the Space SDK:** Select **Docker** (Crucial!).
   - **Docker Template:** Select **Blank** (Do not choose any pre-configured template).
   - **Space Hardware:** Select **CPU basic (Free)**. This is fully sufficient since TERA's routing features run on lightweight CPU-only lexical engines.
   - **Privacy:** Choose **Public** (to share with judges) or **Private**.
4. Click **Create Space** at the bottom of the page.

---

## 3. Configuring Environment Secrets

TERA requires credentials to query the Fireworks API and perform inference. You must configure these as **Variables and Secrets** in the Space settings (never commit them to git!).

1. In your newly created Space, click on the **Settings** tab (gear icon at the top right of the Space navigation bar).
2. Scroll down to the **Variables and secrets** section.
3. Click **New secret** to add your Fireworks credential:
   - **Name:** `FIREWORKS_API_KEY`
   - **Value:** *Paste your actual Fireworks API key (e.g., `fw_...`)*
   - Click **Save**.
4. Click **New variable** (variables are public configurations):
   - **Name:** `FIREWORKS_BASE_URL`
   - **Value:** `https://api.fireworks.ai/inference/v1`
   - Click **Save**.
5. Click **New variable** again:
   - **Name:** `ALLOWED_MODELS`
   - **Value:** `accounts/fireworks/models/deepseek-v4-pro,accounts/fireworks/models/gpt-oss-120b`
   - Click **Save**.

---

## 4. Connecting and Deploying Code

Hugging Face Spaces are backed by a Git repository. You can deploy TERA either by pushing directly to the Hugging Face Git remote, or by syncing it with your GitHub repository.

### Option A: Syncing with GitHub (Recommended)
1. In the Space settings, scroll to the **GitHub Integration** section.
2. Follow the prompt to connect your GitHub account and authorize access.
3. Select your `TERA` repository and choose the `main` branch to sync.
4. Enabling **Automatic Sync** will redeploy the Space every time you push to your GitHub `main` branch.

### Option B: Pushing Directly to Hugging Face Git
1. Clone your Space repository locally (find the HTTPS URL under the "Use Git" button on the Space page):
   ```bash
   git clone https://huggingface.co/spaces/<your-username>/<space-name>
   ```
2. Copy all TERA repository files into the cloned folder.
3. Commit and push the changes:
   ```bash
   git add .
   git commit -m "Deploy TERA to Hugging Face"
   git push origin main
   ```

---

## 5. Build and Startup Monitoring

1. Once the code is pushed or synced, navigate to the **App** tab in your Hugging Face Space.
2. The page will show **Building** while it executes the multi-stage Docker build:
   - **Stage 1 (frontend-builder):** Installs Node.js dependencies and compiles the Next.js frontend to static HTML (`out/`).
   - **Stage 2 (production):** Installs Python dependencies (FastAPI, scikit-learn, etc.), copies pre-trained models and compiled frontend assets, and setups the entrypoint.
3. To view detailed build progress, click on **See logs** in the building notification bar.
4. **Expected Startup Log Output:**
   ```
   ====================================
   TERA Track 1 Production Startup
   ====================================
   Launching TERA Web Server on port 7860...
   INFO:     Started server process [1]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:7860 (Press CTRL+C to quit)
   ```

---

## 6. Troubleshooting Deployment Failures

- **Error: `AttributeError: 'Text' object has no property 'lineheight'` during build:**
  Verify that the presentation asset generation or matplotlib calls in any executed scripts do not use properties incompatible with the installed matplotlib version. (Resolved in our latest release).
- **Error: `uvicorn` command not found:**
  Ensure the `PYTHONPATH` env variable is set to `/app/backend` and dependencies are successfully installed via `requirements.txt` in the Dockerfile.
- **Service starts up but fails to load pages:**
  Confirm that your Space is configured to use the **Docker** SDK, not a Python template, as the frontend requires compilation and packaging.
- **Inference returns 403 or 401 Forbidden:**
  Check that your `FIREWORKS_API_KEY` secret is named exactly `FIREWORKS_API_KEY` (case-sensitive) and has no leading or trailing whitespace.
- **Port conflicts:**
  Hugging Face Spaces routes HTTP traffic to port **7860**. Do not change the `--port 7860` parameter in the entrypoint command.

---

## 7. Management and Updates

- **Restarting the Space:** If the application encounters an unrecoverable failure or needs a fresh boot, navigate to Settings and click **Restart Space**.
- **Updating Configurations:** If you rotate your Fireworks API keys, update the secret in Settings and restart the Space.
