from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.db.session import get_db, engine, Base
from src.db.seed import init_db_and_seed

# App metadata for OpenAPI
app = FastAPI(
    title="StreamView Backend",
    description="FastAPI backend for a simple streaming application with SQLite + SQLAlchemy.",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Placeholder for future routers
# from src.api.routers import auth, videos, categories
# app.include_router(auth.router, prefix="/auth", tags=["auth"])
# app.include_router(videos.router, prefix="/videos", tags=["videos"])
# app.include_router(categories.router, prefix="/categories", tags=["categories"])


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
