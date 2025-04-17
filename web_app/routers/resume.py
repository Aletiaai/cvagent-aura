# Purpose: Define API endpoints for resume processing (upload, triggering Drive processing, etc.). This replaces the interactive input() logic from your current main.py.
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
# Import your agent's execution logic (we'll define this later)
# from agent.core.execution import trigger_resume_processing_from_file, trigger_resume_processing_from_drive
import shutil 
from pathlib import Path 

# Define UPLOAD_DIR here as well if needed, or import from a central config
UPLOAD_DIR_RESUME = Path("data/resumes")
UPLOAD_DIR_RESUME.mkdir(parents=True, exist_ok=True)

router = APIRouter()

async def process_and_save_resume(background_tasks: BackgroundTasks, file: UploadFile):
    """Saves the resume and triggers background processing."""
    if not file.filename.lower().endswith(".pdf"):
        # Raise exception to be caught by the calling route
        raise HTTPException(status_code=400, detail="Tipo de archivo invalido. Solo archivos PDF son aceptados.")

    # Use a safe path - consider making filename unique later
    save_path = UPLOAD_DIR_RESUME / file.filename
    print(f"Attempting to save file via resume router logic to: {save_path}")

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"File '{file.filename}' saved successfully via resume router logic.")
    except Exception as e:
        print(f"Error saving file in resume router logic: {e}")
        # Raise a different exception type or handle as needed
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
    finally:
        # Ensure file is closed even if saving fails
        await file.close() # Close the file stream passed in

    # Trigger background processing by the agent (Placeholder)
    # background_tasks.add_task(trigger_resume_processing_from_file, str(save_path), file.filename)
    print(f"Placeholder: Background processing triggered via resume router logic for {file.filename}.")

# The API endpoint simply calls the processing function
@router.post("/upload/file/", name="upload_resume_api")
async def upload_resume_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """API endpoint for uploading a resume file."""
    # No need to close file here, process_and_save_resume will do it
    await process_and_save_resume(background_tasks=background_tasks, file=file)
    return {"message": f"File '{file.filename}' received and processing started."}

@router.post("/trigger/drive/")
async def trigger_drive_processing(background_tasks: BackgroundTasks, drive_folder_path: str):
    # Trigger background processing for Drive
    # background_tasks.add_task(trigger_resume_processing_from_drive, drive_folder_path)
    return {"message": f"Processing triggered for Drive folder: {drive_folder_path}"}
    
# Add more endpoints as needed (e.g., get status, get results)


# Note: You'll need functions like trigger_resume_processing_from_file and trigger_resume_processing_from_drive in your agent/core/execution.py which this router will call. Using BackgroundTasks is crucial for long-running processes like LLM calls.