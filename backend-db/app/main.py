from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db import create_tables


create_tables()


app = FastAPI(
    title="CivicResolveAI",
    description=(
        "AI-powered civic complaint reporting "
        "and resolution platform"
    ),
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


app.include_router(router)


@app.get("/")
def root():

    return {
        "application": "CivicResolveAI",
        "message": "CivicResolveAI backend is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health():

    return {
        "status": "healthy"
    }