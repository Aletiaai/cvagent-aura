# Purpose: Orchestrate the steps defined by planning.py (or embed the planning logic). This replaces the main processing loops in your current main.py and parts of handle_resume_from_drive.py.
# Import necessary functions from other modules
import asyncio

from fastapi import HTTPException
from agent.tools.information_extraction import get_resume_text_from_pdf, extract_information
from agent.core.general_feedback import general_analyzer, general_analyzer_df
from agent.core.asking_questions import complementary_questions
from agent.memory.data_handler import load_data, save_data, save_feedback_to_csv, log_email_sent # Add DataFrame load/save too
from agent.tools.email_sender import email_body_creation, email_body_creation_with_df, send_feedback_email_2, questions_email_draft, email_body_creation_asking_questions # Import email tools
from agent.tools.email_reader import search_emails, get_message, get_attachments # Import email reader tools (if needed for triggering)
from integration.google.drive_api import get_folder_id, list_files_in_folder, download_file # Import Drive tools
from agent.memory.user_db.users import add_resume_sections
# Maybe import planning: from agent.core.planning import plan_resume_processing
import time
import os
import uuid
import pandas as pd # If using DataFrames

async def raw_resume_processing(pdf_bytes: bytes, uid: str):
    """Main execution flow for a single uploaded file."""
    try:
        # 1. Extract text
        text = get_resume_text_from_pdf(pdf_bytes)
        if not text:
            print(f"Empty text extracted for user {uid}")
            return False
        
        print(f"Este es el texto extraido (primeros 200 caracteres): {text[:200]}...\n{'═'*50}")
        
        # 2. Extract structured data
        extracted_data = extract_information(text, "user_extract_all_sections")
        if not extracted_data:
            print(f"Failed to extract information for user {uid}")
            return False
        
        # 3. Debug print extracted data safely
        if isinstance(extracted_data, dict):
            print("Extracted sections:")
            for section, content in extracted_data.items():
                print(f"  {section}: {str(content)[:100]}...")
        else:
            print(f"Raw extracted data: {str(extracted_data)[:200]}...")
        
        # 4. Save to Firestore
        await add_resume_sections(uid, extracted_data)
        return True
    
    except Exception as e:
        print(f"El procesamiento iniicial del CV fallo para el usuario: {uid}: {str(e)}")
        import traceback
        traceback.print_exc()  # Full stack trace
        raise

     












# --- Functions to be called by web_app routers (or CLI) ---

def trigger_resume_processing_from_file(file_path: str, original_filename: str, analyze=True, ask_questions=False, send_email=True):
    """Main execution flow for a single uploaded file."""
    print(f"Executing processing for file: {original_filename}")
    try:
        resume_text = get_resume_text_from_pdf(file_path)
        if not resume_text:
            print(f"Could not extract text from {original_filename}")
            return

        # --- DataFrame Path ---
        # processor = ResumeProcessor() # Assuming ResumeProcessor is defined/imported
        # candidate_id = processor.process_resume(file_path)
        # if candidate_id:
        #    processor.save_to_csv("data/processed_resumes")
        #    if analyze:
        #        feedback = analyze_resume_with_df(candidate_id, original_filename)
        #    if send_email:
        #        email_body_creation_with_df(candidate_id) # Handles draft creation + logging
        # --- OR Dictionary Path ---
        resume_array = load_data() # Start fresh
        resume_array["CandidateID"] = str(uuid.uuid4())
        resume_array["file_path"] = file_path
        resume_array["resume_text"] = resume_text

        extracted_data = extract_information(resume_array, resume_text, "extracted_sections", "user_extract_all_sections")
        if not extracted_data:
            print(f"Extraction failed for {original_filename}")
            return
        
        save_data(resume_array, original_filename) # Save intermediate state

        if analyze:
            feedback_result = general_analyzer(resume_array["extracted_sections"]) # Pass extracted sections
            # Update resume_array and save again if needed
            if feedback_result and "error" not in feedback_result:
                resume_array["general_feedback"] = feedback_result
                save_data(resume_array, original_filename) # Save with feedback
                if send_email:
                    email_body = email_body_creation(resume_array, feedback_result)
                    # email_body_creation now calls send_feedback_email_2 internally
                    # which returns draft info, but this top-level function might not need it.
                    print(f"Email draft created for {original_filename}")
            else:
                 print(f"Feedback generation failed for {original_filename}")

        elif ask_questions: # Mutually exclusive with analyze? Your choice.
             questions = complementary_questions(resume_array, original_filename) # Saves data internally
             if questions and "error" not in questions:
                 if send_email:
                    email_body, user_name, recipient_email = email_body_creation_asking_questions(resume_array, questions)
                    if email_body:
                        questions_email_draft(recipient_email, user_name, email_body)
                        print(f"Questions email draft created for {original_filename}")
             else:
                print(f"Question generation failed for {original_filename}")


    except Exception as e:
        print(f"Error processing file {original_filename}: {e}")
        import traceback
        traceback.print_exc()
    finally:
         # Optional: Clean up temp file
         # if os.path.exists(file_path):
         #    os.remove(file_path)
         pass

def trigger_resume_processing_from_drive(drive_folder_path: str, service_type: str = "review"):
    """Main execution flow for processing files from a Drive folder."""
    print(f"Executing Drive processing for folder: {drive_folder_path}")
    drive_folder_id = get_folder_id(drive_folder_path)
    if not drive_folder_id:
        print(f"Could not find Drive folder: {drive_folder_path}")
        return

    try:
        # This function needs access to the Drive service object
        # Maybe pass it in, or initialize it within the function/class
        files = list_files_in_folder(drive_folder_id) # Assumes service is available
        total_files = len(files)
        print(f"Found {total_files} files in Drive folder.")

        for index, file in enumerate(files):
            print(f"\nProcessing file {index + 1} of {total_files}: {file['name']}")
            if not file['name'].lower().endswith(".pdf"):
                print(f"Skipping non-PDF file: {file['name']}")
                continue

            # --- Download Step ---
            download_dir = "data/user_resumes_drive"
            download_file(file['id'], file['name'], download_dir) # Assumes service is available
            resume_path = os.path.join(download_dir, file['name'])

            # --- Process Step (Similar logic to trigger_resume_processing_from_file) ---
            # Adapt the logic from process_resume_from_drive, analyze_resume, etc. here
            # Choose dictionary or DataFrame path
            try:
                if service_type == "review":
                    # Dictionary Path Example
                    resume_text = get_resume_text_from_pdf(resume_path)
                    if not resume_text: continue
                    resume_array = load_data()
                    resume_array["CandidateID"] = str(uuid.uuid4())
                    # ... rest of extraction ...
                    extract_information(resume_array, resume_text, "extracted_sections", "user_extract_all_sections")
                    save_data(resume_array, file['name'])
                    feedback_result = general_analyzer(resume_array["extracted_sections"])
                    if feedback_result and "error" not in feedback_result:
                        resume_array["general_feedback"] = feedback_result
                        save_data(resume_array, file['name'])
                        email_body = email_body_creation(resume_array, feedback_result)
                        print(f"Email draft created for {file['name']}")

                    # --- OR DataFrame Path Example ---
                    # processor = ResumeProcessor()
                    # candidate_id = processor.process_resume(resume_path)
                    # if candidate_id:
                    #     processor.save_to_csv("data/processed_resumes")
                    #     feedback = analyze_resume_with_df(candidate_id, file['name'])
                    #     if feedback and "error" not in feedback:
                    #         email_body_creation_with_df(candidate_id) # Creates draft

                elif service_type == "enhance": # Corresponds to your old 'v' option
                    # Dictionary Path Example
                    resume_text = get_resume_text_from_pdf(resume_path)
                    if not resume_text: continue
                    resume_array = load_data()
                    resume_array["CandidateID"] = str(uuid.uuid4())
                    # ... rest of extraction ...
                    extract_information(resume_array, resume_text, "extracted_sections", "user_extract_all_sections")
                    save_data(resume_array, file['name'])
                    questions = complementary_questions(resume_array, file['name']) # Saves data internally
                    if questions and "error" not in questions:
                        email_body, user_name, recipient_email = email_body_creation_asking_questions(resume_array, questions)
                        if email_body:
                            questions_email_draft(recipient_email, user_name, email_body)
                            print(f"Questions email draft created for {file['name']}")

            except Exception as e:
                print(f"Error processing specific file {file['name']}: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Optional: Clean up downloaded file
                # if os.path.exists(resume_path):
                #    os.remove(resume_path)
                pass

            # --- Delay ---
            if index < total_files - 1:
                print(f"\nWaiting 10 seconds before next file...")
                time.sleep(10)

    except Exception as e:
        print(f"Error during Drive processing loop: {e}")
        import traceback
        traceback.print_exc()

# You might also move the email processing logic here if needed
# def trigger_resume_processing_from_email(label_name: str): ...

# Note: This file becomes the central orchestrator. It calls functions from core, memory, tools, and integration. It needs careful implementation to handle errors and manage state (like resume_array or candidate_id).
