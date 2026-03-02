"""
X-Tern Agents Backend - FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import cases, health, mcp
from app.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    setup_logging()
    yield


app = FastAPI(
    title="X-Tern Agents API",
    description="Backend API for X-Tern Agents application",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(cases.router, prefix="/cases", tags=["Cases"])
app.include_router(mcp.router, prefix="/mcp", tags=["MCP Tools"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
