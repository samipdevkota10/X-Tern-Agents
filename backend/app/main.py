"""
FastAPI main application for Disruption Response Planner.
"""
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import audit_logs, auth, dashboard, disruptions, governance, pipeline, rag, scenarios
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.models import User
from app.db.session import SessionLocal, engine

# Create FastAPI app
app = FastAPI(
    title="Disruption Response Planner API",
    description="FastAPI backend for multi-agent disruption response planning",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(disruptions.router)
app.include_router(pipeline.router)
app.include_router(scenarios.router)
app.include_router(audit_logs.router)
app.include_router(dashboard.router)
app.include_router(governance.router)
app.include_router(rag.router)


@app.on_event("startup")
def startup_event():
    """
    Application startup event.
    Creates database tables and seeds default users if needed.
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Seed default users if none exist
    db = SessionLocal()
    try:
        user_count = db.query(User).count()

        if user_count == 0:
            # Create default manager
            manager = User(
                user_id=str(uuid.uuid4()),
                username="manager_01",
                hashed_password=get_password_hash("password"[:72]),  # Bcrypt limit
                role="warehouse_manager",
            )
            db.add(manager)

            # Create default analyst
            analyst = User(
                user_id=str(uuid.uuid4()),
                username="analyst_01",
                hashed_password=get_password_hash("password"[:72]),  # Bcrypt limit
                role="analyst",
            )
            db.add(analyst)

            db.commit()
            print("✓ Created default users: manager_01 and analyst_01 (password: 'password')")
    except Exception as e:
        print(f"Warning: Could not seed default users: {e}")
        db.rollback()
    finally:
        db.close()


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Disruption Response Planner API",
        "version": "1.0.0",
        "docs": "/api/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
