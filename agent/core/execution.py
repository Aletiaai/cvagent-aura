# Purpose: Orchestrate the steps defined by planning.py (or embed the planning logic). This replaces the main processing loops in your current main.py and parts of handle_resume_from_drive.py.
# Import necessary functions from other modules

#agent/core/execution.py
from fastapi import HTTPException
from agent.tools.information_extraction import get_resume_text_from_pdf, extract_information
from agent.core.asking_questions import complementary_questions
from agent.memory.data_handler import load_data, save_data, save_feedback_to_csv, log_email_sent # Add DataFrame load/save too
from agent.tools.email_sender import email_body_creation, email_body_creation_with_df, send_feedback_email_2, questions_email_draft, email_body_creation_asking_questions # Import email tools
from agent.tools.email_reader import search_emails, get_message, get_attachments # Import email reader tools (if needed for triggering)
from integration.google.drive_api import get_folder_id, list_files_in_folder, download_file # Import Drive tools
from agent.memory.user_db.users import add_resume_version, fetch_resume_data
from agent.tools.general_feedback import generate_llm_feedback
from googleapiclient.errors import HttpError
from google.cloud import firestore
from agent.tools.google_doc import create_google_doc


class ResumeFeedbackOrchestrator:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state = {"stage": "initialized"}
    
    async def process_raw_resume(self, pdf_bytes: bytes):
        # Extract text and store in Firestore
        success, resume_id= await raw_resume_processing(pdf_bytes, self.user_id)
        if success and resume_id:
            self.state["stage"] = "raw_processed"
            await self.generate_llm_feedback(resume_id)
        return success
    
    async def generate_llm_feedback(self, resume_id: str):
        self.state["stage"] = "generating_llm_feedback"
        # Get resume data from Firestore
        resume_data = await fetch_resume_data(self.user_id, "user", resume_id)
        # Generate LLM feedback
        feedback = await generate_llm_feedback(resume_data)
        # Store feedback in Firestore
        metadata = {
                "created_at": firestore.SERVER_TIMESTAMP,
                "last_updated": firestore.SERVER_TIMESTAMP,
                "model_info": "gemini-2.0-flash-thinking-exp-01-21"
            }
        latest_resume_id = await add_resume_version(self.user_id, feedback, "llm_feedback", resume_id, metadata)
        self.state["stage"] = "llm_feedback_generated"
        llm_feedback_doc_url = await create_google_doc(self.user_id, feedback, "Reporte_de_retroalimentación_v1")

        if llm_feedback_doc_url:
            print(f"Google Doc created successfully: {llm_feedback_doc_url}")
            # Optional: Store the URL, perhaps update Firestore record
            self.state["stage"] = "google_doc_created" # Update state if needed
            # You might want to add the URL to the feedback dict or save it separately
            # feedback['google_doc_url'] = llm_feedback_doc_url # Example
        else:
            print(f"Failed to create Google Doc for user {self.user_id}, resume_id {resume_id}")
            self.state["stage"] = "google_doc_failed" # Update state if needed
            # Decide how to handle failure - maybe log and continue, or raise error

        return feedback


"""    
    async def process_hr_feedback(self, hr_feedback: dict):
        # Store HR's revised feedback
        await add_resume_version(self.user_id, hr_feedback, "hr_feedback")
        self.state["stage"] = "completed"
        return True
"""
    
async def raw_resume_processing(pdf_bytes: bytes, uid: str):
    """Main execution flow for a single uploaded file"""
    try:
        # 1. Extract text
        text = get_resume_text_from_pdf(pdf_bytes)
        if not text:
            print(f"Empty text extracted for user {uid}")
            return False, None
        
        print(f"Este es el texto extraido (primeros 200 caracteres): {text[:200]}...\n{'═'*50}")
        
        # 2. Extract structured data
        extracted_data = extract_information(text, "user_extract_all_sections")
        if not extracted_data:
            print(f"Failed to extract information for user {uid}")
            return False, None
        
        # 3. Debug print extracted data safely
        if isinstance(extracted_data, dict):
            print("Extracted sections:")
            for section, content in extracted_data.items():
                print(f"  {section}: {str(content)[:100]}...")
        else:
            print(f"Raw extracted data: {str(extracted_data)[:200]}...")
        
        # 4. Save user version resume to Firestore
        resume_id = await add_resume_version(uid, extracted_data, "user")
        print(f"CV número: {resume_id} guardado en Firestore para el usuario: {uid}")
        return True, resume_id
    
    except Exception as e:
        print(f"El procesamiento iniicial del CV fallo para el usuario: {uid}: {str(e)}")
        import traceback
        traceback.print_exc()  # Full stack trace
        return False, None

     



# Note: This file becomes the central orchestrator. It calls functions from core, memory, tools, and integration. It needs careful implementation to handle errors and manage state (like resume_array or candidate_id).