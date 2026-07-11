from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging
from app.api.endpoints import router as api_router
from app.api.router_inspector import router as inspector_router

# Initialize structured logging
setup_logging()

app = FastAPI(
    title="TERA Backend",
    description="Token-Efficient Routing Agent (TERA) Backend",
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
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")
app.include_router(api_router)
app.include_router(inspector_router, prefix="/api")
app.include_router(inspector_router)
