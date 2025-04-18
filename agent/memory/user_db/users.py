import uuid
from google.cloud.firestore_v1.async_client import AsyncClient
from datetime import datetime
from config import USERS_COLLECTION, UUID_COLLECTION
from fastapi import HTTPException

db = AsyncClient()

async def check_user_exists(email:str) -> bool:
    """Returns (doc_id, user_data) if exists, else (None, None)."""
    users_ref = db.collection(USERS_COLLECTION)
    query = users_ref.where("email", "==", email).limit(1)
    docs = await query.get()
    for doc in docs:
        print(f"Found user: {doc.id}")
        return True

    return False

async def create_user(email: str, industry: str, expectation: str, confidence: int):
    """Creates a new user document with a UUID and onboarding data."""
    user_uuid = str(uuid.uuid4())
    user_data = {
        "uuid": user_uuid,
        "email": email.lower(), # Store email in lowercase for consistency
        "industry_of_interest": industry,
        "resume_expectation": expectation,
        "resume_confidence": confidence,
        "created_at": datetime.utcnow().isoformat()
    }
    try:
        # 1. Create the user document in USERS_COLLECTION
        doc_ref = db.collection(USERS_COLLECTION).document(user_uuid)
        await doc_ref.set(user_data) 
        print(f"Documento creado para el usuario: {email.lower()} con ID: {user_uuid}")
    
        # 2. Create the email-to-UUID mapping (atomic write)

        uuid_ref = db.collection(UUID_COLLECTION).document(email.lower())
        await uuid_ref.set({"uuid": user_uuid})
        return user_uuid
    except Exception as e:
        print(f"Error al crear el usuario {email.lower()} en Firestore: {e}")
        raise e
    
async def get_uuid_by_email(email: str) -> str:
    """Looks for the uuid, if exists, using the email and returns it."""
    doc_ref = db.collection(UUID_COLLECTION).document(email.lower())
    doc = await doc_ref.get()  # Properly awaited

    if not doc.exists:
        raise HTTPException(status_code=400, detail="El usuraio no fue encontrado")
    return doc.get("uuid")

async def add_hashed_pwd(user_uuid: str, hashed_password: str):
    try:
        # 1. Update email in user document
        await db.collection(USERS_COLLECTION).document(user_uuid).update({
            "hashed_password": hashed_password
        })
    except Exception as e:
        print(f"Error al guardar el password the usuario {user_uuid} en Firestore: {e}")
