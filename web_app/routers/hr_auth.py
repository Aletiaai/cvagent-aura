from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_303_SEE_OTHER, HTTP_401_UNAUTHORIZED
from agent.memory.user_db.users import check_hr_user_exists, get_hr_user_by_email, get_hr_review_data
from agent.tools.pwd.pwd_processing import verify_password
from agent.memory.user_db.users import get_pending_resumes

router = APIRouter(
    tags=["HR Authentication"]
)

templates = Jinja2Templates(directory="web_app/templates")

@router.get("/hr/login", response_class=HTMLResponse, name="get_hr_login_page")
async def get_hr_login_page(request: Request):
    """Serves the HR login page."""
    return templates.TemplateResponse("hr_login.html", {"request": request})

@router.post("/hr/login", name="handle_hr_login")
async def handle_hr_login(request: Request, email: str = Form(...), password: str = Form(...)):
    """Handles HR login form submission and authenticates credentials."""
    if not await check_hr_user_exists(email):
        return templates.TemplateResponse("hr_login.html", {
            "request": request,
            "email": email,
            "error_message": "Correo o password incorrecto."
        }, status_code=HTTP_401_UNAUTHORIZED)
    
    hr_user = await get_hr_user_by_email(email)
    print(f"HR User Data: {hr_user}")
    stored_hash = hr_user.get("hashed_password")
    result = verify_password(password, stored_hash)
    print(f"Verification result: {result}")
    
    if not stored_hash or not verify_password(password, stored_hash):
        return templates.TemplateResponse("hr_login.html", {
            "request": request,
            "email": email,
            "error_message": "Correo o password incorrecto."
        }, status_code=HTTP_401_UNAUTHORIZED)
    
    # Successful authentication
    response = RedirectResponse(url=request.url_for('get_hr_dashboard_page'), status_code=HTTP_303_SEE_OTHER)
    response.set_cookie(key="hr_session", value="logged_in")
    return response


@router.get("/hr/dashboard", response_class=HTMLResponse, name="get_hr_dashboard_page")
async def get_hr_dashboard_page(request: Request):
    """Renders the HR dashboard with the resume review queue."""
    hr_session = request.cookies.get("hr_session")
    if hr_session != "logged_in":  
        return RedirectResponse(
            url=request.url_for("get_hr_login_page"),
            status_code=status.HTTP_303_SEE_OTHER
        )
    
    # Fetch the resume list
    try:
        resume_list = await get_pending_resumes()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching resume queue")
    
    return templates.TemplateResponse(
        "hr_dashboard.html",
        {"request": request, "resumes": resume_list}
    )

@router.get("/hr/review/{user_uuid}/{resume_id}", response_class=HTMLResponse, name="get_hr_review_page")
async def get_hr_review_page(request: Request, user_uuid: str, resume_id: str):
    hr_session = request.cookies.get("hr_session")
    if hr_session != "logged_in":
        return RedirectResponse(
            url=request.url_for("get_hr_login_page"),
            status_code=HTTP_303_SEE_OTHER
        )
    # Fetch review data using the new function
    review_data = await get_hr_review_data(user_uuid, resume_id)
    return templates.TemplateResponse(
        "hr_review.html",
        {
            "request": request,
            **review_data
        }
    )

@router.post("/hr/complete_review/{user_uuid}/{resume_id}", name="complete_review")
async def complete_review(request: Request, user_uuid: str, resume_id: str):
   """Marks the review as complete and updates the resume status."""
   hr_session = request.cookies.get("hr_session")
   if hr_session != "logged_in":
       return RedirectResponse(
           url=request.url_for("get_hr_login_page"),
           status_code=HTTP_303_SEE_OTHER
       )
   
   # Update resume status
   hr_feedback_ref = db.collection("resumes").document(resume_id)
   await hr_feedback_ref.update({
       "metadata.status": "notificacion_pendiente"
   })
   
   return RedirectResponse(
       url=request.url_for("get_hr_dashboard_page"),
       status_code=HTTP_303_SEE_OTHER
   )
