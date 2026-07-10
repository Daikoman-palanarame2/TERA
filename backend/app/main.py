from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging
from app.api.endpoints import router as api_router

# Initialize structured logging
setup_logging()

app = FastAPI(
    title="TERA Backend",
    description="Token-Efficient Routing Agent (TERA) Backend Skeleton",
    version="1.0.0"
)

# Configure CORS Middleware (crucial for React Frontend integration in Phase 4)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to '*' for hackathon simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Router
# Expose endpoints under '/api/v1' namespace and at the root level for developer convenience
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router)
