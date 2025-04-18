# cvagent-aura/web_app/routers/ui_auth.py

import asyncio
from fastapi import APIRouter, Request, Form, Depends, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_303_SEE_OTHER, HTTP_400_BAD_REQUEST
from web_app.routers.resume import process_and_save_resume
from agent.memory.user_db.users import check_user_exists, create_user
from agent.tools.pwd.pwd_processing import get_password_hash, validate_password_complexity
from agent.memory.user_db.users import add_hashed_pwd, get_uuid_by_email

# --- Router Setup ---
# A more robust approach might involve dependency injection for templates if needed across many routers.
templates = Jinja2Templates(directory="web_app/templates") # Define templates within this router file

# --- Industry Data Structure ---
INDUSTRIES_DATA = {
    "Tecnología y TI": [
        "Desarrollo de Software", "Ciberseguridad", "Inteligencia Artificial",
        "Análisis de Datos", "Soporte Técnico", "Redes y Telecomunicaciones"
    ],
    "Salud y Ciencias de la Vida": [
        "Medicina (Médicos, Enfermería)", "Farmacéutica", "Biotecnología",
        "Psicología", "Fisioterapia", "Odontología"
    ],
    "Finanzas y Contabilidad": [
        "Banca", "Inversiones y Bolsa", "Contabilidad y Auditoría",
        "Seguros", "Finanzas Corporativas"
    ],
    "Educación": [
        "Docencia (Primaria, Secundaria, Universitaria)", "Capacitación Corporativa",
        "Educación en Línea", "Investigación Académica"
    ],
    "Ingeniería y Construcción": [
        "Ingeniería Civil", "Ingeniería Mecánica", "Ingeniería Eléctrica",
        "Arquitectura", "Construcción y Obras Públicas"
    ],
    "Manufactura y Producción": [
        "Automotriz", "Textil", "Alimentaria", "Electrónica"
    ],
    "Comercio y Ventas": [
        "Ventas al por Menor", "Comercio Electrónico (E-commerce)",
        "Representante de Ventas", "Atención al Cliente"
    ],
    "Marketing y Publicidad": [
        "Marketing Digital", "Publicidad y Branding", "Redes Sociales",
        "Investigación de Mercados"
    ],
    "Recursos Humanos": [
        "Reclutamiento y Selección", "Desarrollo Organizacional",
        "Capacitación y Desarrollo"
    ],
    "Medios y Entretenimiento": [
        "Cine y Televisión", "Música", "Periodismo", "Producción Audiovisual"
    ],
    "Turismo y Hospitalidad": [
        "Hotelería", "Restaurantes y Gastronomía", "Agencias de Viajes"
    ],
    "Energía y Medio Ambiente": [
        "Energías Renovables", "Petróleo y Gas", "Sostenibilidad Ambiental"
    ],
    "Legal y Gobierno": [
        "Abogacía", "Servicios Públicos", "Política y Relaciones Internacionales"
    ],
    "Logística y Transporte": [
        "Transporte y Distribución", "Cadena de Suministro", "Almacén y Inventario"
    ],
    "Arte y Diseño": [
        "Diseño Gráfico", "Bellas Artes", "Diseño de Interiores"
    ],
    "Deportes y Bienestar": [
        "Entrenamiento Personal", "Nutrición y Dietética", "Deportes Profesionales"
    ],
    "Agricultura y Agroindustria": [
        "Agricultura", "Ganadería", "Agronegocios"
    ],
    "Servicios Profesionales y Consultoría": [
        "Consultoría Empresarial", "Consultoría Tecnológica", "Asesoría Financiera"
    ],
    "Sector Público y ONGs": [
        "Organizaciones No Gubernamentales (ONGs)", "Trabajo Social",
        "Cooperación Internacional"
    ],
    "Otros": [
        "Emprendimiento", "Trabajo Freelance", "Industrias Creativas"
    ]
}
# --- End Industry Data ---

router = APIRouter(
    tags=["UI & Authentication"], # Tag for API docs
    # Dependencies can be added here if needed for all routes in this router
)



# --- Root Route ---
@router.get("/", response_class=HTMLResponse, name="read_root") # Added name for url_for
async def read_root(request: Request):
    """Serves the initial email entry page."""
    return templates.TemplateResponse("index.html", {"request": request})

# --- Email Check Route ---
@router.post("/check-email", name="handle_email_check") # Added name for url_for
async def handle_email_check(request: Request, email: str = Form(...)):
    """Checks if email exists and redirects to login or onboarding."""
    is_existing_user = await check_user_exists(email)
    if is_existing_user:
        print(f"Email {email} found. Redirecting to login.")
        # Use url_for with the router's name for the route
        login_url = request.url_for('get_login_page').include_query_params(email=email)
        return RedirectResponse(url=str(login_url), status_code=HTTP_303_SEE_OTHER)
    else:
        print(f"Email {email} not found. Redirecting to onboarding.")
        onboarding_url = request.url_for('get_onboarding_page').include_query_params(email=email)
        return RedirectResponse(url=str(onboarding_url), status_code=HTTP_303_SEE_OTHER)

# --- Login Routes ---
@router.get("/login", name="get_login_page", response_class=HTMLResponse)
async def get_login_page(request: Request, email: str | None = None):
    """Serves the login page, pre-filling the email if provided."""
    print(f"Serving login page for email: {email}")
    return templates.TemplateResponse("login.html", {"request": request, "email": email})

@router.post("/login", name="handle_login")
async def handle_login_attempt(request: Request, email: str = Form(...), password: str = Form(...)):
    """Handles the login form submission."""
    print(f"Login attempt for email: {email}")
    # --- Placeholder Authentication Logic ---
    authenticated = password == "password" # VERY INSECURE - Placeholder only!
    # --- Replace with actual authentication ---
    if authenticated:
        print(f"Authentication successful for {email}. Redirecting to dashboard.")
        dashboard_url = request.url_for('get_dashboard_page')
        # Set session cookie here in a real app
        return RedirectResponse(url=str(dashboard_url), status_code=HTTP_303_SEE_OTHER)
    else:
        print(f"Authentication failed for {email}.")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "email": email,
            "error_message": "Correo o password incorrecto."
        }, status_code=401)

# --- Onboarding Route ---
@router.get("/onboarding", name="get_onboarding_page", response_class=HTMLResponse)
async def get_onboarding_page(request: Request, email: str | None = None):
    """Serves the onboarding questionnaire page."""
    print(f"Serving onboarding page for: {email}")
    # Pass the industries data to the template context
    return templates.TemplateResponse("onboarding.html", {
        "request": request,
        "email": email,
        "industries_data": INDUSTRIES_DATA
    })

@router.post("/onboarding", name="handle_onboarding")
async def handle_onboarding_submission(
    request: Request,
    email: str = Form(...),
    industry: str = Form(...),
    expectations: str = Form(...),
    confidence_rating: int = Form(...) # FastAPI converts to int
):
    """Handles the onboarding questionnaire submission."""
    print("--- Onboarding Data Received ---")
    print(f"Email: {email}")
    print(f"Industry: {industry}")
    print(f"Expectations: {expectations}")
    print(f"Confidence Rating: {confidence_rating}")
    print("---------------------------------")

    # Save to firestore
    new_user_id = await create_user(
        email = email,
        industry = industry,
        expectation = expectations,
        confidence = confidence_rating
    )

    print(f"User {new_user_id} created and saved to Firestore")

    #Re-direct to resume upload/account creation
    create_account_url = request.url_for('get_create_account_page').include_query_params(uid=new_user_id, email=email)
    return RedirectResponse(url=str(create_account_url), status_code=HTTP_303_SEE_OTHER)

# --- Create Account Route ---
@router.get("/create-account", name="get_create_account_page", response_class=HTMLResponse)
async def get_create_account_page(request: Request, uid: str | None = None, email: str | None = None):
   """Serves the page for resume upload and account creation prompts."""
   print(f"Serving create account/upload page for: {uid}, email: {email}")
   return templates.TemplateResponse("create_account.html", {"request": request, "uid": uid, "email": email})

@router.post("/create-account", name="handle_create_account")
async def handle_create_account_and_upload(
    request: Request,
    background_tasks: BackgroundTasks, # <--- Add BackgroundTasks dependency
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    file: UploadFile = File(...)
):
    """Handles submission of resume and account creation details."""
    print(f"Handling account creation and upload for: {email}")

    # --- Server-Side Validation (Passwords only needed here now) ---
    errors = {}
    if password != confirm_password:
        errors["password_mismatch"] = "Los passwords no coinciden."
    if len(password) < 8:
         errors["password_length"] = "El password debe tener al menos 8 caracteres."
    # File type validation will be handled by process_and_save_resume
    if validate_password_complexity == False:
        print(f"Errores de validación: {errors}")
        # Close the file stream if validation fails early
        await file.close()
        return templates.TemplateResponse("create_account.html", {
            "request": request,
            "email": email,
            "error_message": "Por favor corrige los errores de password.",
            "errors": errors
        }, status_code=HTTP_400_BAD_REQUEST)

    # --- Process Valid Data ---
    try:
         # 1. Hash the password
        print(f"Hashing password for {email}")
        hashed_password = get_password_hash(password) # <--- HASH the password here
        print(f"Password hashed successfully for {email}.")

        # 2. Create User in Database
        #    NOTE: This assumes the onboarding data (industry, expectation, confidence)
        #          will be collected later. If collected now, add them as Form parameters
        #          and pass them to create_user. Let's assume they are collected later for now.
        #          If you need them *now*, you'll need to add those fields to the
        #          create_account.html form and the function signature here.
        #          For now, we'll pass placeholder values or modify create_user.
        #          Let's modify create_user to handle missing optional fields for now.
        print(f"Actualizando documento de usuario con hashed password para: {email} en Firestore...")
        user_uuid = await get_uuid_by_email(email)
        await add_hashed_pwd(user_uuid, hashed_password)
        print(f"Password hash stored in the database for {email}.")

        # 2. Process and Save the uploaded resume file using resume router's logic
        # The process_and_save_resume function will handle file type check,
        # saving, closing the file, and triggering background tasks.
        await process_and_save_resume(background_tasks=background_tasks, file=file)
        # If process_and_save_resume raises an HTTPException, FastAPI handles it.

        # 3. Redirect to success page
        completion_url = request.url_for('get_onboarding_complete_page')
        return RedirectResponse(url=str(completion_url), status_code=HTTP_303_SEE_OTHER)

    except HTTPException as e:
         # If process_and_save_resume raised an expected error (like bad file type)
         # Re-render the form with the specific error from the exception
         print(f"HTTP Exception during resume processing: {e.detail}")
         await file.close() # Ensure file is closed if not already
         errors["file_error"] = e.detail # Add file error to display
         return templates.TemplateResponse("create_account.html", {
            "request": request,
            "email": email,
            "error_message": "Por favor corrige los errores.",
            "errors": errors
         }, status_code=e.status_code) # Use status code from exception

    except Exception as e:
        # Handle other potential errors (e.g., unexpected issues during account creation)
        print(f"Unexpected error processing account/upload: {e}")
        await file.close() # Ensure file is closed
        # Re-render with a generic server error
        errors["server_error"] = "Ocurrió un error interno al procesar tu solicitud."
        return templates.TemplateResponse("create_account.html", {
            "request": request,
            "email": email,
            "error_message": "Error del servidor.",
            "errors": errors
         }, status_code=500)
    # No finally block needed to close file here, as process_and_save_resume handles it on success/failure.

# --- Onboarding Completion Route ---
@router.get("/onboarding-complete", name="get_onboarding_complete_page", response_class=HTMLResponse)
async def get_onboarding_complete_page(request: Request):
    # ... (same as before) ...
    return templates.TemplateResponse("onboarding_complete.html", {"request": request})


# --- Dashboard Route (Placeholder Definition) ---
@router.get("/dashboard", name="get_dashboard_page", response_class=HTMLResponse)
async def get_dashboard_page_placeholder(request: Request):
    """Serves the placeholder dashboard page."""
    print("Serving dashboard page placeholder.")
    # Check login status here in a real app
    # Later: return templates.TemplateResponse("dashboard.html", {"request": request})
    return HTMLResponse("<html><body>User Dashboard (coming soon - from router)</body></html>")

# --- Forgot Password Route (Placeholder Definition) ---
@router.get("/forgot-password", name="get_forgot_password", response_class=HTMLResponse)
async def get_forgot_password_placeholder(request: Request):
    """Serves the placeholder forgot password page."""
    print("Serving forgot password page placeholder.")
    return HTMLResponse("<html><body>Forgot Password Page (coming soon - from router)</body></html>")