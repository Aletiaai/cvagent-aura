#cvagent-aura/agent/memory/user_db/users.py
import uuid
import json
from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore
from datetime import datetime
from config import USERS_COLLECTION, UUID_COLLECTION, RESUME_COLLECTION, HR_COLLECTION, SECTIONS_COLLECTION, user_metadata_template
from fastapi import HTTPException
from typing import Optional, List
import os
from pathlib import Path
from google.oauth2 import service_account

# Set the absolute path to your key file
KEY_PATH = os.path.expanduser("~/.secure-keys/cvagent-sa-key.json")

# Verify the key exists
if not Path(KEY_PATH).exists():
    raise FileNotFoundError(f"Service account key not found at {KEY_PATH}")

# Initialize credentials
credentials = service_account.Credentials.from_service_account_file(
    KEY_PATH,
    scopes=["https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/datastore"]
)

# Create Firestore client with explicit project
db = firestore.AsyncClient(
    credentials=credentials,
    project="stone-passage-456618-i6"  
)

# Verification function (optional but recommended)
async def verify_connection():
    try:
        # Try a simple operation
        test_ref = db.collection("__test__").document("connection_test")
        await test_ref.set({"timestamp": firestore.SERVER_TIMESTAMP})
        await test_ref.delete()
        print(f"✓ Successfully connected to Firestore project: {db.project}")
    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        raise


async def check_user_exists(email:str) -> bool:
    """Returns (doc_id, user_data) if exists, else (None, None)."""
    users_ref = db.collection(USERS_COLLECTION)
    query = users_ref.where("email", "==", email).limit(1)
    docs = await query.get()
    for doc in docs:
        print(f"Found user: {doc.id}")
        return True

    return False

async def create_user(email: str, industry: str) -> str:
    """Creates a new user document with a UUID and onboarding data."""
    user_uuid = str(uuid.uuid4())
    user_data = {
        "uuid": user_uuid,
        "email": email.lower(), # Store email in lowercase for consistency
        "industry_of_interest": industry,
        "created_at": firestore.SERVER_TIMESTAMP
    }
    try:
        # Create user document
        # 1. Create the user and resume document in USERS_COLLECTION and RESUME_COLLECTION
        doc_ref = db.collection(USERS_COLLECTION).document(user_uuid)
        await doc_ref.set(user_data)
        #resume_ref = db.collection(RESUME_COLLECTION).document(user_uuid)
        #await resume_ref.add(resume_data)
        print(f"Documento creado para el usuario: {email.lower()} con ID: {user_uuid}")
    
        # Create email-to-UUID mapping
        # 2. Create the email-to-UUID mapping (atomic write)

        uuid_ref = db.collection(UUID_COLLECTION).document(email.lower())
        await uuid_ref.set({"user_id": user_uuid})
        return user_uuid
    except Exception as ve:
        print(f"Validation error creating user {email.lower()}: {ve}")
        raise
    except Exception as e:
        print(f"Error creating user {email.lower()} in Firestore: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")
    
async def get_uuid_by_email(email: str) -> str:
    """Looks for the uuid, if exists, using the email and returns it."""
    doc_ref = db.collection(UUID_COLLECTION).document(email.lower())
    doc = await doc_ref.get()  # Properly awaited

    if not doc.exists:
        raise HTTPException(status_code=400, detail="El usuraio no fue encontrado")
    return doc.get("user_id")

async def add_hashed_pwd(user_uuid: str, hashed_password: str):
    try:
        # 1. Update hashed password in user document
        await db.collection(USERS_COLLECTION).document(user_uuid).update({
            "hashed_password": hashed_password
        })
    except Exception as e:
        print(f"Error al guardar el password the usuario {user_uuid} en Firestore: {e}")

async def add_resume_version(resume_data: str | dict, metadata: dict = None) -> str:
    """Adds or updates a resume version for a user."""
    try:
        # Validate input
        if not resume_data:
            raise ValueError("Resume data cannot be empty")
        version_type = metadata.get("version_type")
        resume_id = metadata.get("resume_id")
        user_uid = metadata.get("user_id")
        user_uuid = str(user_uid)  # Convert to string if not already
        
        valid_versions = ["user", "llm", "llm_feedback", "hr", "hr_feedback", "master"]
        if version_type not in valid_versions:
            raise ValueError(f"Version type must be one of: {', '.join(valid_versions)}")

        # Consistent field names
        user_id_field = "user_id"
        version_field = "version"
        content_field = "content"
        metadata_field = "metadata"
        created_at_field = "created_at"
        last_updated_field = "last_updated"
        
        # Create or get resume document
        if resume_id:
            # Update existing resume
            resume_ref = db.collection(RESUME_COLLECTION).document(resume_id)
            resume_doc = await resume_ref.get()
            if not resume_doc.exists:
                raise ValueError(f"Resume {resume_id} does not exist")
            existing_data = resume_doc.to_dict()

            # Ensure version matches
            if existing_data[version_field] != version_type:
                raise ValueError(f"Resume {resume_id} is version {existing_data[version_field]}, not {version_type}")
            
            # For "user" version, check if update is allowed
            if version_type == "user":
                is_complete = existing_data.get(metadata_field, {}).get("is_complete", False)
                if is_complete:
                    raise ValueError(f"'user' version for user {user_uuid} is already complete and cannot be updated")
            
            update_data = {
                "content_field": resume_data,
                "last_updated_field": firestore.SERVER_TIMESTAMP
            }
            if metadata:
                update_data[metadata_field] = metadata
            elif version_type == "user":
                update_data[metadata_field] = {**existing_data.get(metadata_field, {}), "is_complete": True}
            await resume_ref.update(update_data)
            return resume_ref.id
        else:
            # Create new resume (only for "user" version)
            if version_type != "user":
                raise ValueError("resume_id is required for non-user versions")
            
            # Check for existing "user" version
            query = db.collection(RESUME_COLLECTION).where(filter=FieldFilter(user_id_field, "==", user_uuid)).where(filter=FieldFilter(version_field, "==", "user"))
            docs = await query.get()
            if docs:
                # Update existing "user" version if not complete
                resume_ref = docs[0].reference
                existing_data = docs[0].to_dict()
                if existing_data.get(metadata_field, {}).get("is_complete", False):
                    raise ValueError(f"A complete 'user' version already exists for user {user_uuid}")
                
                update_data = {
                    content_field: resume_data,
                    last_updated_field: firestore.SERVER_TIMESTAMP,
                    metadata_field: {**existing_data.get(metadata_field, {}), "is_complete": True}
                }

                await resume_ref.update(update_data)
                return resume_ref.id
            else:
                # Create new "user" version with onboarding data
                resume_ref = db.collection(RESUME_COLLECTION).document()
                print(f"Este es el id del CV: {resume_ref.id}")
                metadata["created_at"] = firestore.SERVER_TIMESTAMP
                metadata["last_updated"] = firestore.SERVER_TIMESTAMP
                metadata["resume_id"] = resume_ref.id 
                new_resume_data = {
                    content_field: resume_data,
                    metadata_field: metadata,
                }
                await resume_ref.set(new_resume_data)

                #Adding the user_resume_id to the user document
                user_ref = db.collection(USERS_COLLECTION).document(user_uuid)
                await user_ref.update({
                    "user_resume_id": resume_ref.id
                })

                return resume_ref.id
        
    except ValueError as ve:
        print(f"Validation error for user {user_uuid}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error saving resume version for user {user_uuid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save resume version: {str(e)}")

async def fetch_resume_data(user_id: str, resume_id: str) -> str:
    """Looks for the uuid, if exists, using the email and returns it."""
    try:
        # Construct the document reference path
        version_ref = (
            db.collection(RESUME_COLLECTION)
            .document(resume_id)
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
    
    
async def check_hr_user_exists(email: str) -> bool:
    """Checks if an HR user exists by email."""
    hr_users_ref = db.collection(HR_COLLECTION)
    query = hr_users_ref.where("email", "==", email.lower()).limit(1)
    docs = await query.get()
    return len(docs) > 0

async def get_hr_user_by_email(email: str) -> dict:
    """Retrieves HR user data by email."""
    hr_users_ref = db.collection(HR_COLLECTION)
    query = hr_users_ref.where("email", "==", email.lower()).limit(1)
    docs = await query.get()
    if not docs:
        raise HTTPException(status_code=404, detail="HR user not found")
    return docs[0].to_dict()


async def get_pending_resumes():
    """Fetches resumes in 'en revisión' and 'pendiente' statuses, ordered by submission date."""
    resumes_ref = db.collection_group(RESUME_COLLECTION)
    
    # Query for "En Revisión" resumes
    in_review_query = (
        resumes_ref
        .where(filter=FieldFilter("metadata.status", "==", "en revisión"))
        .order_by("metadata.created_at", direction=firestore.Query.ASCENDING)
        .limit(50)
    )
    try:
        in_review_docs = await in_review_query.get()
    except Exception as e:
        print(f"Error fetching 'en revisión' resumes: {str(e)}")
        raise Exception("Error fetching 'En Revisión' resumes")
    
    # Query for "Pendiente" resumes
    remaining_limit = 50 - len(in_review_docs)
    pending_query = (
        resumes_ref
        .where(filter=FieldFilter("metadata.status", "==", "pendiente"))
        .order_by("metadata.created_at", direction=firestore.Query.ASCENDING)
        .limit(remaining_limit)
    )
    try:
        pending_docs = await pending_query.get()
    except Exception as e:
        print(f"Error fetching pendiente' resumes: {str(e)}")
        raise Exception("Error fetching 'pendiente' resumes")
    
    
    # Combine results: "En Revisión" first, then "Pendiente"
    all_docs = list(in_review_docs) + list(pending_docs)
    
    # Extract and format data
    resume_list = []
    for doc in all_docs:
        resume_data = doc.to_dict()
        user_uuid = resume_data["metadata"]["user_id"]
        google_doc_url = resume_data["metadata"].get("google_doc_url")
        submission_date = (
            resume_data["metadata"]["created_at"].isoformat()
            if resume_data["metadata"].get("created_at")
            else "Unknown"
        )
        resume_list.append({
            "user_uuid": user_uuid,
            "google_doc_url": google_doc_url,
            "resume_id": doc.id,
            "submission_date": submission_date,
            "industry": resume_data["metadata"]["onboarding"].get("industry") if resume_data["metadata"].get("onboarding") else resume_data["metadata"].get("industry", "Unknown"),
            "status": resume_data["metadata"].get("status", "Unknown")
        })
    return resume_list

async def get_hr_review_data(user_uuid: str, resume_id: str):
    # Fetch user data
    user_ref = db.collection(USERS_COLLECTION).document(user_uuid)
    user_doc = await user_ref.get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = user_doc.to_dict()
    
    # Fetch original resume document (version_type == "user")
    original_resume_query = db.collection(RESUME_COLLECTION).where("metadata.user_id", "==", user_uuid).where("metadata.version_type", "==", "llm_feedback").limit(1)
    original_resume_docs = await original_resume_query.get()
    if not original_resume_docs:
        raise HTTPException(status_code=404, detail="Original resume not found")
    original_resume_doc = original_resume_docs[0].to_dict()
    
    # Fetch LLM feedback document
    llm_feedback_ref = db.collection(RESUME_COLLECTION).document(resume_id)
    llm_feedback_doc = await llm_feedback_ref.get()
    if not llm_feedback_doc.exists:
        raise HTTPException(status_code=404, detail="LLM feedback not found")
    llm_feedback_data = llm_feedback_doc.to_dict()
    
    # Extract necessary data
    user_details = user_data
    resume_metadata = original_resume_doc['metadata']
    user_pdf_url = user_details.get('pdf_url', 'no_pdf_url')
    llm_google_doc_edit_url = llm_feedback_data['metadata'].get('google_doc_url', 'no_google_doc_url')
    llm_feedback_resume_id = resume_id
    
    return {
        "user_details": user_details,
        "resume_metadata": resume_metadata,
        "user_pdf_url": user_pdf_url,
        "llm_google_doc_edit_url": llm_google_doc_edit_url,
        "llm_feedback_resume_id": llm_feedback_resume_id
    }