from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.db.session import get_db, engine, Base
from src.db.seed import init_db_and_seed

# Routers
from src.api.routers import auth as auth_router
from src.api.routers import videos as videos_router
from src.api.routers import categories as categories_router
from src.api.routers import stream as stream_router

openapi_tags = [
    {"name": "health", "description": "Service health and diagnostics"},
    {"name": "auth", "description": "Authentication endpoints (JWT)"},
    {"name": "videos", "description": "Video catalog and metadata"},
    {"name": "categories", "description": "Video categories"},
    {"name": "stream", "description": "Video streaming with HTTP Range support"},
]

# App metadata for OpenAPI
app = FastAPI(
    title="StreamView Backend",
    description="FastAPI backend for a simple streaming application with SQLite + SQLAlchemy.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# CORS - allow Authorization header and expose Range/Content-Range for streaming
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization", "Range"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length", "Content-Type"],
)

# Include routers
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(videos_router.router, prefix="/videos", tags=["videos"])
app.include_router(categories_router.router, prefix="/categories", tags=["categories"])
app.include_router(stream_router.router, prefix="/stream", tags=["stream"])


@app.on_event("startup")
def on_startup():
    """
    Initialize the database and seed sample data on app startup.
    """
    # Ensure tables exist (extra safety; seed also calls create_all)
    Base.metadata.create_all(bind=engine)

    # Seed initial data using a short-lived session
    from src.db.session import db_session
    with db_session() as db:
        init_db_and_seed(db)


# PUBLIC_INTERFACE
@app.get("/", summary="Health Check", tags=["health"])
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.

    Parameters:
        db: SQLAlchemy session dependency to verify DB access is healthy.

    Returns:
        dict: {"message": "Healthy"}
    """
    # Quick lightweight DB touch to assert session works
    _ = db.execute("SELECT 1").scalar()
    return {"message": "Healthy"}
