# Purpose: Define API endpoints for resume processing (upload, triggering Drive processing, etc.). This replaces the interactive input() logic from your current main.py.
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
# Import your agent's execution logic (we'll define this later)
# from agent.core.execution import trigger_resume_processing_from_file, trigger_resume_processing_from_drive

router = APIRouter()

@router.post("/upload/file/")
async def upload_resume_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is supported.")
    
    # Save the uploaded file temporarily (or process in memory if feasible)
    temp_file_path = f"data/resumes/{file.filename}" # Or use tempfile module
    with open(temp_file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    # Trigger background processing by the agent
    # background_tasks.add_task(trigger_resume_processing_from_file, temp_file_path, file.filename) 
    
    return {"message": f"File '{file.filename}' received and processing started."}

@router.post("/trigger/drive/")
async def trigger_drive_processing(background_tasks: BackgroundTasks, drive_folder_path: str):
    # Trigger background processing for Drive
    # background_tasks.add_task(trigger_resume_processing_from_drive, drive_folder_path)
    return {"message": f"Processing triggered for Drive folder: {drive_folder_path}"}
    
# Add more endpoints as needed (e.g., get status, get results)


# Note: You'll need functions like trigger_resume_processing_from_file and trigger_resume_processing_from_drive in your agent/core/execution.py which this router will call. Using BackgroundTasks is crucial for long-running processes like LLM calls.