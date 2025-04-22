#core/information_extractor.py
import os
import json
import fitz
from io import BytesIO
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from integration.llm.gemini_api import GeminiAPI
from config import PROMPTS

gemini_api = GeminiAPI()
    
def get_resume_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts text from PDF bytes (no file saved)."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text.strip() if text else None
    except Exception as e:
        print(f"Error extrayendo texto de PDF: {e}")
        return None
    
class RateLimitException(Exception):
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(RateLimitException)
)

def retry_generate_content(prompt):
    try:
        response = gemini_api.generate_content(prompt)
        if not response:
            raise ValueError("Empty response from Gemini API")
        return response
    except Exception as e:
        if "429" in str(e) or "Resource has been exhausted" in str(e):
            print("Rate limit hit, waiting before retry...")
            raise RateLimitException(str(e))
        raise
    
def extract_information(resume_txt: str, prompt_key: str) -> dict:
    """Extracts structured information from resume text using LLM."""
    # Input validation
    if not resume_txt:
        print("⚠️ Empty resume text provided")
        return None
        
    if prompt_key not in PROMPTS:
        print(f"⚠️ Prompt key '{prompt_key}' not found")
        return None

    # Initialize variables
    response_text = None
    parsed_data = None

    # LLM Communication
    try:
        prompt = PROMPTS[prompt_key].format(resume_data=resume_txt)
        response = retry_generate_content(prompt)
        
        if not response:
            print("⚠️ Empty response from LLM")
            return None
            
        response_text = str(response).strip()
        
        # Response Parsing
        try:
            response_text = clean_json_response(response_text)
            parsed_data = json.loads(response_text)
            
            if not validate_resume_structure(parsed_data):
                return None

            return parsed_data
            
        except json.JSONDecodeError as e:
            print(f"🔴 JSON parsing error: {e}")
            if response_text:  # Only show response if it exists
                print(f"Problematic response (500 chars):\n{response_text[:500]}...")
            return None
        except Exception as e:
            print(f"🔴 Unexpected parsing error: {e}")
            return None

    except RateLimitException as e:
        print(f"⏳ Rate limited: {e}")
        return None
    except Exception as e:
        print(f"🔥 LLM communication error: {e}")
        return None


def clean_json_response(response_text: str) -> str:
    """Extracts JSON from markdown code blocks if present."""
    if not response_text:
        return ""
        
    response_text = response_text.strip()
    if '```json' in response_text:
        return response_text.split('```json')[1].split('```')[0].strip()
    if '```' in response_text:
        return response_text.split('```')[1].split('```')[0].strip()
    return response_text


def validate_resume_structure(data: dict, structure=None) -> bool:
    """Validates resume structure while allowing empty sections."""
    if structure is None:
        # Define the structure only on initial call
        structure = {
            "user_info": {
                "first_name": (str, type(None)),
                "last_name": (str, type(None)),
                "email": (str, type(None)),
                "phone_number": (str, type(None)),
                "linkedin_profile": (str, type(None)),
                "address": (str, type(None)),
            },
            "summary": (str, type(None)),
            "skills": {
                "soft_skills": (list, type(None)),
                "hard_skills": (list, type(None))
            },
            "relevant_work_experience": (list, type(None)),
            "education": (list, type(None)),
            "languages": (list, type(None))
        }

    if not isinstance(data, dict):
        print("⚠️ Top-level data is not a dictionary")
        return False
        
    for key, expected_type in structure.items():
        if key not in data:
            print(f"⚠️ Missing required section: {key}")
            return False
            
        # Skip validation if value is None (empty section)
        if data[key] is None:
            continue
            
        # Handle nested dictionaries
        if isinstance(expected_type, dict):
            if not isinstance(data[key], dict):
                print(f"⚠️ Expected dictionary for section: {key}")
                return False
            if not validate_resume_structure(data[key], expected_type):
                return False
        # Handle type checking
        elif not isinstance(data[key], expected_type):
            if isinstance(expected_type, tuple):
                if not any(isinstance(data[key], t) for t in expected_type):
                    print(f"⚠️ Type mismatch for {key}. Expected {expected_type}, got {type(data[key])}")
                    return False
            else:
                if not isinstance(data[key], expected_type):
                    print(f"⚠️ Type mismatch for {key}. Expected {expected_type}, got {type(data[key])}")
                    return False
                
    return True