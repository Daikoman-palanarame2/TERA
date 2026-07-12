import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.logging import setup_logging
from app.api.endpoints import router as api_router
from app.api.router_inspector import router as inspector_router

from app.core.config import settings, ENTROPY_THRESHOLD, MIN_PROBABILITY_FLOOR, MODEL_TIMEOUT_SEC, FALLBACK_RETRY_COUNT
from app.cache.semantic_cache import SemanticCache
from app.parser.intent_parser import IntentParser
from app.solvers.solver_registry import SolverRegistry
from app.solvers.plugins.arithmetic_solver import ArithmeticSolver
from app.solvers.plugins.logic_solver import LogicSolver
from app.solvers.plugins.text_counter_solver import TextCounterSolver
from app.solvers.plugins.word_problem_solver import WordProblemSolver
from app.inference.local_client import LocalModelClient
from app.inference.local_power_client import LocalPowerModelClient
from app.inference.remote_client import RemoteModelClient
from app.verification.rovl import ROVL
from app.core.orchestrator import TERAOrchestrator

# Initialize structured logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Initialization logic:
    # 1. Instantiate semantic cache
    cache = SemanticCache(
        cache_dir=settings.tera_cache_dir,
        embedding_model_path=settings.tera_onnx_model_path
    )
    
    # 2. Instantiate and register solvers
    registry = SolverRegistry()
    registry.register_solver(ArithmeticSolver())
    registry.register_solver(LogicSolver())
    registry.register_solver(TextCounterSolver())
    registry.register_solver(WordProblemSolver())
    registry.lock()
    
    # 3. Instantiate intent parser
    parser = IntentParser(registry)
    
    # 4. Local model client
    local_client = LocalModelClient(
        endpoint_url=settings.tera_local_inference_url,
        model_name=settings.tera_local_model_name,
        timeout_sec=settings.tera_model_timeout_sec
    )
    
    # 5. Power tier: local vLLM by default; Fireworks is explicit opt-in only.
    if settings.tera_external_fallback_enabled:
        if not settings.tera_fireworks_api_key:
            raise RuntimeError(
                "TERA_FIREWORKS_API_KEY is required when external fallback is enabled."
            )
        remote_client = RemoteModelClient(
            api_key=settings.tera_fireworks_api_key,
            endpoint_url=settings.tera_fireworks_api_url,
            model_name=settings.tera_remote_model_name,
            max_retries=FALLBACK_RETRY_COUNT
        )
    else:
        remote_client = LocalPowerModelClient(
            endpoint_url=settings.tera_power_inference_url,
            model_name=settings.tera_power_model_name,
            timeout_sec=settings.tera_model_timeout_sec
        )
    
    # 6. ROVL Verification
    rovl = ROVL(
        entropy_threshold=ENTROPY_THRESHOLD,
        min_prob_floor=MIN_PROBABILITY_FLOOR
    )
    
    # 7. Core TERA V2 Orchestrator
    orchestrator = TERAOrchestrator(
        cache=cache,
        parser=parser,
        registry=registry,
        local_client=local_client,
        remote_client=remote_client,
        rovl=rovl,
        settings=settings
    )
    
    # Expose the orchestrated pipeline globally
    app.state.orchestrator = orchestrator
    
    yield
    
    # Shutdown / Connection cleanup logic:
    await local_client.close()
    await remote_client.close()
    cache.env.close()

app = FastAPI(
    title="TERA Backend",
    description="Token-Efficient Routing Agent (TERA) Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware (crucial for React Frontend integration)
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

@app.get("/health")
async def root_health():
    """
    Returns simple health confirmation payload.
    """
    return {"status": "ok"}

@app.get("/ready")
async def root_ready():
    """
    Returns simple readiness confirmation payload.
    """
    return {"status": "ok"}

# Conditionally serve static Next.js frontend files if compiled folder exists

static_dir = "/app/frontend/out"
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    local_static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/out"))
    if os.path.exists(local_static_dir):
        app.mount("/", StaticFiles(directory=local_static_dir, html=True), name="static")
