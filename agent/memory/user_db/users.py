import uuid
from google.cloud.firestore_v1.async_client import AsyncClient
from datetime import datetime
from config import USERS_COLLECTION

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
        "email": email,
        "industry_of_interest": industry,
        "resume_expectation": expectation,
        "resume_confidence": confidence,
        "created_at": datetime.utcnow().isoformat()
    }
    await db.collection(USERS_COLLECTION).document(user_uuid).set(user_data)
    return user_uuid
