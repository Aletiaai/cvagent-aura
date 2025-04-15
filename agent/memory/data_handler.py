#data/data_handler.py
import json
import re
import os
import ast

import pandas as pd
import fitz  # PyMuPDF
import uuid
import hashlib
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from datetime import datetime


from integration.llm.gemini_api import GeminiAPI

DATA_DIR = "data/resumes"
DATA_FILE = "data/resume_data.json"
PROMPTS_DIR = "prompts"
gemini_api = GeminiAPI()

def ensure_data_directory():
    """Ensures the data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def generate_filename(resume_name):
    """Generates a unique filename for each resume"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean the resume name to create a valid filename
    clean_name = "".join(c for c in resume_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    return f"{clean_name}_{timestamp}.json"

def load_data():
    """Returns an empty dictionary for a new resume"""
    return {}

def save_data_2(data, original_filename=None):
    """Saves resume data to a unique file"""
    ensure_data_directory()
    
    # Generate a filename based on the original PDF name if available
    if original_filename:
        base_name = os.path.splitext(os.path.basename(original_filename))[0]
    else:
        base_name = "resume"
    
    filename = os.path.join(DATA_DIR, generate_filename(base_name))
    
    try:
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data, filename
    except Exception as e:
        print(f"Error saving resume data: {str(e)}")
        return None, None
    
def save_data(data, original_filename=None):
    """Saves resume data to a unique file with a name based on first name, last name, and CandidateID."""
    ensure_data_directory()

    # Extract user information for the file name
    user_info = data.get("extracted_sections", {}).get("user_info", {})
    first_name = user_info.get("first_name", "Unknown").replace(" ", "_").title()
    last_name = user_info.get("last_name", "Unknown").replace(" ", "_").title()
    candidate_id = data.get("CandidateID", "UnknownID").replace(" ", "_")
    
    # Generate the file name based on user information
    if first_name != "Unknown" and last_name != "Unknown" and candidate_id != "UnknownID":
        base_name = f"{first_name}_{last_name}_{candidate_id}"
    elif original_filename:
        base_name = os.path.splitext(os.path.basename(original_filename))[0]
    else:
        base_name = "resume"

    # Construct the full file path
    filename = os.path.join(DATA_DIR, f"{base_name}.json")

    try:
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data, filename
    except Exception as e:
        print(f"Error saving resume data: {str(e)}")
        return None, None    
    
def format_work_experience(work_experience_str):
    try:
        # If it's already a list, format it
        if isinstance(work_experience_str, list):
            return format_work_experience_list(work_experience_str)
        
        # If it's a string, try to parse it
        if isinstance(work_experience_str, str):
            # Clean up the string first
            cleaned_str = work_experience_str.strip()
            if cleaned_str.startswith("[") and cleaned_str.endswith("]"):
                try:
                    # Try using json.loads first with some preprocessing
                    # Replace single quotes with double quotes for JSON compatibility
                    json_str = cleaned_str.replace("'", '"')
                    work_experience = json.loads(json_str)
                    return format_work_experience_list(work_experience)
                except json.JSONDecodeError:
                    try:
                        # If JSON parsing fails, try ast.literal_eval
                        work_experience = ast.literal_eval(cleaned_str)
                        return format_work_experience_list(work_experience)
                    except (ValueError, SyntaxError) as e:
                        print(f"Error parsing work experience string: {e}")
                        # Return a cleaned up version of the string
                        return clean_and_format_raw_text(cleaned_str)
            else:
                # If it's not a list format, return cleaned text
                return clean_and_format_raw_text(cleaned_str)
        
        return ""  # Return empty string if none of the above work
        
    except Exception as e:
        print(f"Error in format_work_experience: {e}")
        return str(work_experience_str)  # Return as-is if all else fails

def format_work_experience_list(work_experience):
    """Helper function to format a list of work experiences"""
    formatted_text = ""
    for job in work_experience:
        # Add job header
        formatted_text += f"\n{job.get('title', 'Unknown Position')} at {job.get('company', 'Unknown Company')}"
        if job.get('dates'):
            formatted_text += f" ({job['dates']})"
        if job.get('location'):
            formatted_text += f" - {job['location']}"
        formatted_text += "\n"
        
        # Add description if it exists
        if job.get('description'):
            # If description is a string of bullet points, keep them as is
            description = job['description']
            if isinstance(description, str):
                # Ensure proper spacing for bullet points
                description = description.replace('* ', '\n* ').strip()
                formatted_text += f"{description}\n"
            else:
                formatted_text += f"{str(description)}\n"
        
        formatted_text += "\n"  # Add extra space between jobs
    return formatted_text

def clean_and_format_raw_text(text):
    """Helper function to clean and format raw text"""
    # Remove unnecessary escape characters
    cleaned = text.replace('\\n', '\n').replace('\\t', '\t')
    # Remove multiple consecutive newlines
    cleaned = '\n'.join(line for line in cleaned.splitlines() if line.strip())
    return cleaned  # Add this return statement

def get_candidate_feedback(candidate_id):
    """
    Retrieve the flattened feedback for a specific candidate.
    
    Args:
        candidate_id (str): The ID of the candidate
        
    Returns:
        dict: The flattened feedback or None if not found
    """
    try:
        feedback_df = pd.read_csv("data/processed_resumes/feedback.csv")
        candidate_feedback = feedback_df[feedback_df['candidate_id'] == candidate_id]
        
        if candidate_feedback.empty:
            return None
        
        # Return the most recent feedback if multiple exist
        return candidate_feedback.sort_values('timestamp', ascending=False).iloc[0].to_dict()
        
    except FileNotFoundError:
        print("No feedback file found")
        return None
    except Exception as e:
        print(f"Error retrieving feedback: {e}")
        return None
    
def save_feedback_to_csv(candidate_id, feedback_result, file_name):
    """Save feedback to a CSV file with flattened structure - no nested JSON. Args: candidate_id (str): The ID of the candidate, feedback_result (dict): The feedback to save, file_name (str): The original file name (for reference)"""
    try:
        # Create a feedback dataframe if it doesn't exist
        try:
            feedback_df = pd.read_csv("data/processed_resumes/feedback.csv")
        except FileNotFoundError:
            # Create a dataframe with all the flattened columns we need
            columns = [
                'candidate_id',
                'file_name',
                'timestamp',
                'summary_feedback',
                'summary_example',
                'hard_skills_feedback',
                'hard_skills_example',
                'soft_skills_feedback',
                'soft_skills_example',
                'work_experience_feedback',
                'work_experience_example',
                'education_feedback',
                'education_example',
                'languages_feedback',
                'languages_example'
            ]
            feedback_df = pd.DataFrame(columns=columns)
        
        # Prepare new row with flattened structure
        new_row = {
            'candidate_id': candidate_id,
            'file_name': file_name,
            'timestamp': datetime.now().isoformat()
        }
        
        # Extract and flatten the nested feedback structure
        if 'general_feedback' in feedback_result:
            sections = feedback_result['general_feedback'].get('sections', {})

            # Add summary section feedback and example if available
            if 'summary' in sections:
                new_row['summary_feedback'] = sections['summary'].get('feedback', '')
                new_row['summary_example'] = sections['summary'].get('example', '')
            
            # Add split skills sections (hard and soft) if available
            if 'skills' in sections:
                skills_section = sections['skills']
                
                # Check if skills are already split in the response
                if 'hard_skills' in skills_section:
                    new_row['hard_skills_feedback'] = skills_section['hard_skills'].get('feedback', '')
                    new_row['hard_skills_example'] = skills_section['hard_skills'].get('example', '')
                    new_row['soft_skills_feedback'] = skills_section['soft_skills'].get('feedback', '')
                    new_row['soft_skills_example'] = skills_section['soft_skills'].get('example', '')
                else:
                    # If not split, use the general skills feedback for both (not ideal but prevents data loss)
                    new_row['hard_skills_feedback'] = skills_section.get('feedback', '')
                    new_row['hard_skills_example'] = skills_section.get('example', '')
                    new_row['soft_skills_feedback'] = skills_section.get('feedback', '')
                    new_row['soft_skills_example'] = skills_section.get('example', '')
            
            # Add other sections' feedback and example
            for section_name, section_data in sections.items():
                if section_name not in ['summary', 'skills']:
                    new_row[f'{section_name}_feedback'] = section_data.get('feedback', '')
                    new_row[f'{section_name}_example'] = section_data.get('example', '')
        
        # Add row to dataframe
        feedback_df = pd.concat([feedback_df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Save dataframe
        feedback_df.to_csv("data/processed_resumes/feedback.csv", index=False)
        
        print(f"Saved flattened feedback for candidate {candidate_id}")
        
    except Exception as e:
        print(f"Error saving feedback: {e}")

def log_email_sent(candidate_id, email, email_body, draft_id, draft_message_id, draft_message_thread_id, draft_message_label_id):
    """Log email sending in a CSV file
    
    Args:
        candidate_id (str): The candidate ID
        email (str): The email address
        email_body (str): The email body content
    """
    try:
        # Create or load email logs dataframe
        try:
            email_logs_df = pd.read_csv("data/logs/email_logs.csv")
        except FileNotFoundError:
            email_logs_df = pd.DataFrame(columns=[
                'candidate_id', 'email', 'timestamp', 'draft_created', 'email_body', 'draft_id', 'draft_message_id', 'draft_message_thread_id', 'draft_message_label_id'
            ])
        
        # Add new log entry
        new_row = {
            'candidate_id': candidate_id,
            'email': email,
            'timestamp': pd.Timestamp.now().isoformat(),
            'draft_created': True,
            'email_body':email_body,
            'draft_id':draft_id,
            'draft_message_id':draft_message_id,
            'draft_message_thread_id':draft_message_thread_id,
            'draft_message_label_id':draft_message_label_id
        }
        
        # Add row to dataframe
        email_logs_df = pd.concat([email_logs_df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Save dataframe
        email_logs_df.to_csv("data/logs/email_logs.csv", index=False)
        
        print(f"Logged email sent to {email}")
        
    except Exception as e:
        print(f"Error logging email sent: {e}")
