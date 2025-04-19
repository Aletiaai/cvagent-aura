from fastapi import UploadFile, HTTPException, BackgroundTasks
from pathlib import Path 
import shutil 

UPLOAD_DIR_RESUME = Path("data/resumes")
UPLOAD_DIR_RESUME.mkdir(parents=True, exist_ok=True)



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