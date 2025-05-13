import os
import logging # Use logging for better output control
from passlib.context import CryptContext

# --- Security ---
# Create a CryptContext instance, specifying the schemes to use.
# bcrypt is the recommended default.
# "deprecated="auto"" will automatically mark older hashes as deprecated if you change schemes later.
#pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12,)  # Adjust based on your security needs)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__ident="2b",  # Explicitly set bcrypt ident
)

user_metadata_template = {
    "onboarding": {
        "expectations": None,  # You can set initial values or None
        "confidence_rating": None,
        "industry": None
    },
    "version_type": None, # "user", "llm", "llm_feedback", "hr", "hr_feedback", or "master"
    "created_at": None,
    "last_updated": None,
    "is_complete": False,
    "user_id": None,
    "resume_id": None,
}

llm_feedback_metadata_template = {
    "status": None,
    "version_type": None, # "user", "llm", "llm_feedback", "hr", "hr_feedback", or "master"
    "model_info": None,
    "created_at": None,
    "last_updated": None,
    "user_id": None,
    "resume_id": None,
}

USERS_COLLECTION = "users"
UUID_COLLECTION = "emails_to_uuids"
RESUME_COLLECTION = "resumes"
SECTIONS_COLLECTION = "sections"
HR_COLLECTION = "hr_users"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


PROMPTS = {}

prompt_files = {
    "user_extract_all_sections": ("extraction", "user_all_sections_extraction_v2.txt"),
    "resume_analysis": ("analysis", "entire_resume_analyzer_prompt_v7.txt"),
    "email_format": ("output_formatting", "email_format_generator_v1.txt"),
    "resume_generator": ("resume_generation", "resume_generator.txt"),
    "questions_for_users": ("user_interaction", "q_for_users_v1.txt")
}

# --- Helper Function ---
def load_prompt(filepath):
    """Loads a prompt from the given full filepath."""
    try:
        # Now, open the filepath directly, don't join with PROMPTS_DIR here
        with open(filepath, "r", encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        # Give a more specific error message
        log.error(f"Prompt file not found at {filepath}")
        return None
    except Exception as e:
        log.error(f"Error loading prompt file {filepath}: {str(e)}")
        return None
    
# --- Main Loading Function ---
def load_all_prompts():
    """Loads all defined prompts into the global PROMPTS dictionary."""
    global PROMPTS # Ensure we modify the module-level dictionary

    log.info("Attempting to load prompts...")

    # --- Method 1: Path relative to this config.py file ---
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_prompt_dir = os.path.join(script_dir, "prompts") # 'prompts' is sibling to config.py
    except NameError:
         log.error("Could not determine script directory (__file__ not defined). Cannot load prompts relative to script.")
         base_prompt_dir = None # Handle this case if __file__ might be unavailable

    # --- Method 2: Using Environment Variable (Uncomment to use, overrides Method 1 if set) ---
    # env_prompt_dir = os.environ.get('PROMPT_DIR_PATH')
    # if env_prompt_dir:
    #     base_prompt_dir = env_prompt_dir
    #     log.info(f"Using prompt directory from PROMPT_DIR_PATH: {base_prompt_dir}")
    # elif not base_prompt_dir: # Only log warning if relative path also failed
    #      log.warning("PROMPT_DIR_PATH environment variable not set. Trying default relative path.")


    if not base_prompt_dir or not os.path.isdir(base_prompt_dir):
        log.critical(f"Prompt directory not found or invalid: {base_prompt_dir}. Cannot load prompts.")
        return # Stop loading

    log.info(f"Loading prompts from base directory: {base_prompt_dir}")

    # Define subfolders based on the determined base path
    prompt_folders = {
        "extraction": os.path.join(base_prompt_dir, "extraction"),
        "user_interaction": os.path.join(base_prompt_dir, "user_interaction"),
        "output_formatting": os.path.join(base_prompt_dir, "output_formatting"),
        "analysis": os.path.join(base_prompt_dir, "analysis"),
        "resume_generation": os.path.join(base_prompt_dir, "resume_generation")
    }

    loaded_count = 0
    for key, (folder_key, filename) in prompt_files.items():
        folder_path = prompt_folders.get(folder_key)
        if not folder_path:
            log.warning(f"Folder key '{folder_key}' for prompt '{key}' not defined in prompt_folders.")
            continue

        full_filepath = os.path.join(folder_path, filename)
        prompt_content = load_prompt(full_filepath)

        if prompt_content is not None:
            PROMPTS[key] = prompt_content
            loaded_count += 1
            # log.debug(f"Successfully loaded prompt '{key}'") # Use debug level for verbose
        else:
            log.warning(f"Failed to load prompt content for key '{key}' from file '{full_filepath}'")

    log.info(f"Prompt loading complete. Loaded {loaded_count}/{len(prompt_files)} prompts.")
    if loaded_count < len(prompt_files):
         log.warning("Some prompts failed to load. Check logs above.")

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
# Example: GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
