# Purpose: Initialize the FastAPI application and include routers.
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles # Import StaticFiles
from fastapi.templating import Jinja2Templates # Import Jinja2Templates
from .routers import resume, ui_auth # Import the new ui_auth router
import config # Import your config module (uncomment if using)


# --- Setup for Templates and Static Files ---
# Make sure these paths are correct relative to where you run the app
templates = Jinja2Templates(directory="web_app/templates")
static_files_path = "web_app/static"

async def startup_event():
    """Load prompts during FastAPI startup."""
    config.load_all_prompts()

app = FastAPI(title="CV Agent API", on_startup=[startup_event]) # Use this if you need startup events

# Mount static files directory
# Ensure the path "web_app/static" exists and contains your 'css/styles.css'
app.mount("/static", StaticFiles(directory=static_files_path), name="static")

# Include routers here if you use them
app.include_router(ui_auth.router)
app.include_router(resume.router, prefix="/api/v1/resume", tags=["Resume API"]) # Example prefix

# --- End Setup ---

print("FastAPI app initialized with routers.")