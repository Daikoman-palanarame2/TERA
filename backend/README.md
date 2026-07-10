# TERA FastAPI Backend

Token-Efficient Routing Agent (TERA) backend built using FastAPI.

## Setup and Running

1. **Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Running the Server**:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

## Key API Endpoints

- **Health check**: `GET /health` -> Returns service health.
- **Routing**: `POST /api/v1/route` -> Processes routing requests.
