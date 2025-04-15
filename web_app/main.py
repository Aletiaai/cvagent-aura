# Purpose: Initialize the FastAPI application and include routers.
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles # Import StaticFiles
from fastapi.templating import Jinja2Templates # Import Jinja2Templates
from fastapi.responses import HTMLResponse # Import HTMLResponse
# If you use routers (recommended):
from .routers import resume # Assuming you create resume.py in routers
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
# --- End Setup ---

# Include routers here if you use them
app.include_router(resume.router, prefix="/api/v1/resume", tags=["Resume Processing"]) # Example prefix


# Modified root route to serve the index.html template
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Pass the request object to the template
    return templates.TemplateResponse("index.html", {"request": request})

# Add other global routes or middleware if needed

# --- Placeholder Endpoint for Email Check (Add to main.py or a new router) ---
# You'll likely move this to a dedicated auth router later

from fastapi import Form, Depends # Need Form for form data
from fastapi.responses import RedirectResponse # To redirect user
from starlette.status import HTTP_303_SEE_OTHER # For POST redirect

# Placeholder function to simulate database check
async def check_user_exists(email: str) -> bool:
    print(f"Checking database for email: {email}")
    # --- !!! ---
    # Replace this with your actual database lookup logic
    # Example: user = await database.get_user_by_email(email)
    # return user is not None
    # --- !!! ---
    # For now, let's pretend emails containing 'test' are existing users
    await asyncio.sleep(0.5) # Simulate db lookup time
    return 'test' in email.lower()

import asyncio # Import asyncio for the sleep example

@app.post("/check-email")
async def handle_email_check(request: Request, email: str = Form(...)):
    """
    Receives the email from the form, checks if the user exists,
    and redirects to the appropriate next step.
    """
    is_existing_user = await check_user_exists(email)

    if is_existing_user:
        # Redirect to the login page (we'll create this in the next step)
        # We'll pass the email in the URL query for pre-filling, but using
        # secure sessions would be better in a real application.
        print(f"Email {email} found. Redirecting to login.")
        # Using status_code 303 is important for POST redirects
        login_url = request.url_for('get_login_page').include_query_params(email=email)
        return RedirectResponse(url=str(login_url), status_code=HTTP_303_SEE_OTHER)
    else:
        # Redirect to the onboarding page (we'll create this later)
        print(f"Email {email} not found. Redirecting to onboarding.")
        onboarding_url = request.url_for('get_onboarding_page').include_query_params(email=email)
        return RedirectResponse(url=str(onboarding_url), status_code=HTTP_303_SEE_OTHER)

# --- Placeholder Routes for redirection targets (define these properly later) ---
@app.get("/login", name="get_login_page", response_class=HTMLResponse)
async def get_login_page_placeholder(request: Request, email: str | None = None):
    # This will be replaced by the actual login page rendering
    # return f"Login page for {email}"
    # For now, render a placeholder or the final template if ready
    return templates.TemplateResponse("login.html", {"request": request, "email": email}) # Assuming login.html exists

@app.get("/onboarding", name="get_onboarding_page", response_class=HTMLResponse)
async def get_onboarding_page_placeholder(request: Request, email: str | None = None):
    # This will be replaced by the actual onboarding page rendering
    # return f"Onboarding page for {email}"
    # For now, render a placeholder or the final template if ready
    return templates.TemplateResponse("onboarding.html", {"request": request, "email": email}) # Assuming onboarding.html exists