from config import pwd_context
from passlib.context import CryptContext
from fastapi import HTTPException
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hashed version.
    Returns True if match, False otherwise.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification failed: {str(e)}")
        return False
    
# --- Helper function for password verification (useful for login later) ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# --- Helper function for hashing ---
def get_password_hash(password):
    """
    Hash a password using the most secure available method.
    Falls back to alternative schemes if primary fails.
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Primary hashing failed, attempting fallback: {str(e)}")
        try:
            # Explicitly try Argon2 if bcrypt fails
            return pwd_context.hash(password, scheme="argon2")
        except Exception as fallback_error:
            logger.critical(f"All hashing methods failed: {str(fallback_error)}")
            raise HTTPException(
                status_code=500,
                detail="System error: Could not secure password"
            )
        
def validate_password_complexity(password: str, confirm_password: str) -> tuple[bool, dict]:
    """Check if password meets complexity requirements"""
    errors = {}
    if password != confirm_password:
        errors["password_mismatch"] = "Los passwords no coinciden."
    if len(password) < 8:
         errors["password_length"] = "El password debe tener al menos 8 caracteres."
    #if not any(char.isupper() for char in password):
    #    errors["password_uppercase"] = "El password debe contener al menos una letra mayúscula."
    #if not any(char.islower() for char in password):
    #    errors["password_lowercase"] = "El password debe contener al menos una letra minúscula."
    #if not any(char.isdigit() for char in password):
    #    errors["password_digit"] = "El password debe contener al menos un número."
    return (len(errors) == 0, errors)