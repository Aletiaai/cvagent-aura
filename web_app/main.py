# Purpose: Initialize the FastAPI application and include routers.
from fastapi import FastAPI
# If you use routers (recommended):
# from .routers import resume # Assuming you create resume.py in routers
import config # Import your config module

# app.include_router(resume.router) # Include your routers

async def startup_event():
    """Load prompts during FastAPI startup."""
    config.load_all_prompts()

app = FastAPI(title="CV Agent API", on_startup=[startup_event])


# Include routers here if you use them
# app.include_router(resume.router, prefix="/api/v1/resume", tags=["Resume Processing"]) 

@app.get("/")
async def root():
    return {"message": "Welcome to the CV Agent API"}

# Add other global routes or middleware if needed