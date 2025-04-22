import uuid
import json
from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud import firestore
from datetime import datetime
from config import USERS_COLLECTION, UUID_COLLECTION, RESUME_COLLECTION, SECTIONS_COLLECTION
from fastapi import HTTPException

db = AsyncClient()

import uuid

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

async def add_resume_version(
    user_uuid: str, 
    resume_data: str | dict,
    version_type: str,  # "user", "llm", "llm_feedback", "hr", "hr_feedback", or "master"
    resume_id: str = None,       # Optional: provide existing resume_id
    metadata: dict = None,       # Additional metadata for version
):
    try:
        # Validate input
        if not resume_data:
            raise ValueError("Resume data cannot be empty")
            
        if isinstance(resume_data, str):
            resume_data = json.loads(resume_data)
        elif not isinstance(resume_data, dict):
            raise ValueError("Resume data must be a string or dictionary")
        
        valid_versions = ["user", "llm", "llm_feedback", "hr", "hr_feedback", "master"]
        if version_type not in valid_versions:
            raise ValueError(f"Version type must be one of: {', '.join(valid_versions)}")
        
        # Get user reference
        user_ref = db.collection(USERS_COLLECTION).document(user_uuid)
        
        # Create or get resume document
        if resume_id:
            resume_ref = user_ref.collection(RESUME_COLLECTION).document(resume_id)
        else:
            # Only create new resume_id for user version
            if version_type != "user":
                raise ValueError("resume_id is required for non-user versions")
            resume_ref = user_ref.collection(RESUME_COLLECTION).document()
            
            # Initialize metadata for new resume
            await resume_ref.set({
                "metadata": {
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "last_updated": firestore.SERVER_TIMESTAMP,
                    "title": metadata.get("title", "Resume") if metadata else "Resume"
                }
            })
        
        # Add processed_at timestamp
        resume_data["processed_at"] = firestore.SERVER_TIMESTAMP
        
        # Add version-specific metadata
        if version_type == "llm" and metadata:
            resume_data["model_info"] = metadata.get("model_info", {})
        elif version_type == "llm_feedback" and metadata:
            resume_data["model_info"] = metadata.get("model_info", {})
        elif version_type == "hr" and metadata:
            resume_data["reviewer_id"] = metadata.get("reviewer_id", "")
            resume_data["notes"] = metadata.get("notes", "")
        elif version_type == "hr_feedback" and metadata:
            resume_data["reviewer_id"] = metadata.get("reviewer_id", "")
        elif version_type == "master" and metadata:
            resume_data["creator_id"] = metadata.get("creator_id", "")
            resume_data["notes"] = metadata.get("notes", "")
        
        # Store the version
        await resume_ref.collection("versions").document(version_type).set(resume_data)
        
        # Update last_updated timestamp
        await resume_ref.update({
            "metadata.last_updated": firestore.SERVER_TIMESTAMP
        })
        
        return resume_ref.id
        
    except ValueError as ve:
        print(f"Validation error for user {user_uuid}: {ve}")
        raise
    except Exception as e:
        print(f"Error saving resume version for user {user_uuid}: {e}")
        raise

async def fetch_resume_data(user_id: str, version: str, resume_id: str) -> str:
    """Looks for the uuid, if exists, using the email and returns it."""
    try:
        # Construct the document reference path
        version_ref = (
            db.collection(USERS_COLLECTION)
            .document(user_id)
            .collection("resumes")
            .document(resume_id)
            .collection("versions")
            .document(version)
        )

        # Fetch the document
        doc = await version_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="Resume version 'user' not found for the specified resume"
            )
        # Return all document data (resume sections)
        return doc.to_dict()
    
    except Exception as e:
        print(f"Error fetching resume sections for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch resume data: {str(e)}"
        )