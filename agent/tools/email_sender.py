# Encapsulate email creation and sending logic.
# Important: These functions will need access to the Gmail service object. You'll need to manage how this is passed or initialized (e.g., create an EmailSender class that holds the service).
from integration.google.gmail_api import authenticate_gmail_api
from agent.memory.data_handler import save_data

def format_feedback_content(feedback_dict):
    """Formats the feedback dictionary into a readable email body text."""
    email_content = []
    
    # Add email intro
    email_content.append(feedback_dict['email_intro'])
    email_content.append("\n")
    
    # Add each section's feedback
    for section, content in feedback_dict['sections'].items():
         # Section header
        email_content.append(f" {section.replace('_', ' ').title()} \n")
        
        # Add feedback
        email_content.append("Retroalimentación:")
        # Clean up the feedback text by removing markdown if present
        feedback_text = content['feedback']
        feedback_text = feedback_text.replace('**', '').replace('*', '•')
        email_content.append(feedback_text)
        email_content.append("\n")

        # Add example
        email_content.append("Ejemplo:")
        # If example is a dictionary or list, format it for readability
        example = content['example']
        if isinstance(example, (dict, list)) or str(example).strip().startswith('{') or str(example).strip().startswith('['):
            # Convert string representation of dict/list to actual object if needed
            if isinstance(example, str):
                try:
                    import ast
                    example = ast.literal_eval(example)
                except:
                    pass
            if isinstance(example, (dict, list)):
                # Format dictionaries and lists in a readable way
                formatted_example = format_structured_data(example)
            else:
                formatted_example = example
        else:
            formatted_example = example
            
        email_content.append(formatted_example)
        email_content.append("\n")

    # Add closing message
    email_content.append(feedback_dict['closing'])
    
    # Join all parts with proper spacing
    return "\n".join(email_content)

def format_structured_data(data, indent=0):
    """Helper function to format dictionaries and lists in a readable way."""
    if isinstance(data, dict):
        formatted = []
        for key, value in data.items():
            key_str = key.replace('_', ' ').title()
            if isinstance(value, (dict, list)):
                formatted.append(f"{'  ' * indent}{key_str}:")
                formatted.append(format_structured_data(value, indent + 1))
            else:
                formatted.append(f"{'  ' * indent}{key_str}: {value}")
        return '\n'.join(formatted)
    elif isinstance(data, list):
        formatted = []
        for item in data:
            if isinstance(item, (dict, list)):
                formatted.append(format_structured_data(item, indent + 1))
            else:
                formatted.append(f"{'  ' * indent}• {item}")
        return '\n'.join(formatted)
    else:
        return str(data)
    
def format_feedback_content_API_call(feedback):
    """Helper function to extract the feedback from the json or dictionary and set it into a easy to read email with an API call"""
    try:
        feedback_email_format = ""
        prompt_content = load_prompt("email_format_generator_v1.txt")
        formatted_prompt = prompt_content.format(json_api_response = feedback)

        feedback_email_format = gemini_api.generate_content(formatted_prompt)
        return feedback_email_format
    except Exception as e:
        print(f"An error ocurred when formating the responso into an email body: {e}")
        return None

def create_draft(user_id, message_body):
    """Creates a draft email in the user's Gmail account.
    Args:service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
        message_body: The body of the email message, including headers.
    Returns: Draft object, including draft id and message meta data.
    """
    try:
        message = {'message': message_body}
        draft = service.users().drafts().create(userId = user_id, body = message).execute()

        draft_id = draft["id"]
        draft_message = draft["message"]
        draft_message_id = draft["message"]["id"]
        draft_message_thread_id = draft["message"]["threadId"]
        draft_message_label_id = draft["message"]["labelIds"]

        print (f'Draft id: {draft_id}\nDraft message: {draft_message}')
        
        return draft, draft_id, draft_message_id, draft_message_thread_id, draft_message_label_id
    except Exception as e:
        print(f'An error ocurred {e}')
        return None

def send_feedback_email_2(recipient_email, user_name, feedback):
    """Creates a draft email with an ambedded link to a document. The feedback is already formated for an email"""
    try:
        # Create the multipart message
        message = MIMEMultipart()
        message['To'] = recipient_email
        message['From'] = 'marko.garcia@gmail.com'
        message['Subject'] = f"Hola {user_name.title()}, aquí la retro de tu cv"
        message['Cc'] = 'anaya.rjose@gmail.com' # Add the "cc" recipient

        # Format the feedback dictionary into readable text
        #formatted_feedback = format_feedback_content_API_call(feedback)
        formatted_feedback = feedback.replace("\n", "<br>")

        # Add the extra line with a hyperlink
        #extra_tips_link = "https://drive.google.com/file/d/1DB1bbSw3vruC3r5SbwXyOLJJNmwJO9TD/view?usp=drive_link"  # link to the PDF in drive
        #extra_tips_text = (
        #    "Tenemos un extra para ti, "
        #    f'<a href="{extra_tips_link}">aquí</a> '
        #    "puedes encontrar un documento con tips adicionales que pueden ser de ayuda."
        #)

        # Combine the formatted feedback and the extra tips text
        email_body = f"{formatted_feedback}<br>¡Éxito en tu búsqueda laboral!<br>Iván Anaya y Marco García"

        # Add HTML body to email
        message.attach(MIMEText(email_body, 'html', 'utf-8'))
        

        # Encode the message for the Gmail API
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')

        draft_and_info = create_draft("me", {'raw': encoded_message})

        draft, draft_id, draft_message_id, draft_message_thread_id, draft_message_label_id = draft_and_info

        # Create the draft
        return draft, draft_id, draft_message_id, draft_message_thread_id, draft_message_label_id
    except Exception as e:
        print(f"An error occurred while creating the draft email: {e}")
        return None

def questions_email_draft(recipient_email, user_name, email_content):
    try:
        # Create the multipart message
        message = MIMEMultipart()
        message['To'] = recipient_email
        message['From'] = 'marko.garcia@gmail.com'
        message['Subject'] = f"Hola {user_name.title()}, tengo algunas preguntas acerca de tu CV"
        message['Cc'] = 'anaya.rjose@gmail.com' # Add the "cc" recipient

         # Add body to email
        message.attach(MIMEText(email_content, 'plain', 'utf-8'))
        # Encode the message for the Gmail API
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')
        # Create the draft
        return create_draft("me", {'raw': encoded_message})
    except Exception as e:
        print(f"An error occurred while creating the draft: {e}")
        return None

def update_draft_with_attachment(draft_id, pdf_path):
    """Updates an existing draft with a PDF attachment.
    Args:draft_id: The ID of the draft to update
        pdf_path: Path to the PDF file to attach
    Returns:Updated draft object or None if there's an error"""
    try:
        # First, get the existing draft
        draft = service.users().drafts().get(userId = "me", id = draft_id, format = 'full').execute()
        # Create a new message from the existing draft
        message = MIMEMultipart()

        # Copy headers from the original message
        original_headers = draft['message']['payload']['headers']
        for header in original_headers:
            if header['name'].lower() in ['to', 'from', 'subject']:
                message[header['name']] = header['value']

        # Get the original message body
        original_body = None
        parts = draft['message']['payload'].get('parts', [])
        if not parts:  # If no parts, the payload itself might be the message
            if draft['message']['payload'].get('body', {}).get('data'):
                original_body = base64.urlsafe_b64decode(
                    draft['message']['payload']['body']['data'].encode('ASCII')
                ).decode('utf-8')
        else:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    original_body = base64.urlsafe_b64decode(
                        part['body']['data'].encode('ASCII')
                    ).decode('utf-8')
                    break

        # Attach the original body
        if original_body:
             message.attach(MIMEText(original_body, 'plain', 'utf-8'))
        
        # Attach the PDF
        with open(pdf_path, 'rb') as attachment:
            part = MIMEBase('application', 'pdf')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            
            filename = os.path.basename(pdf_path)
            part.add_header(
                'Content-Disposition',
                'attachment',
                filename = filename
            )
            part.add_header('Content-Type', 'application/pdf')
            message.attach(part)

        # Encode the updated message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')
        
        # Update the draft
        updated_draft = service.users().drafts().update(
            userId = "me",
            id = draft_id,
            body = {'message': {'raw': raw_message}}
        ).execute()
        
        print(f'Draft updated with attachment: {draft_id}')
        return updated_draft
    
    except Exception as e:
        print(f'An error occurred while updating draft with the attechment: {e}')
        return None
    
def email_body_creation(resume_array, resume_feedback):
    try:
        # Check if questions is valid
        if not resume_feedback or "error" in resume_feedback:
            print("Invalid or empty feedback dictionary. Cannot create email body.")
            return None
        
        # Getting user info for email
        user_name = resume_array["extracted_sections"]["user_info"]["first_name"].title()
        user_email = resume_array["extracted_sections"]["user_info"]["email"]
        
        # Create the email body
        opening = f"Hola {user_name},\nRevisé tu CV a detalle y tengo algunas observaciones."
        closing = f"Esas son mis observaciones {user_name}, espero que sean de ayuda."
        
        # Extract the feedback from the dictionary
        feedback_info = resume_feedback.get("general_feedback", {}).get("sections", {})
        
        # Convert the feedback dictionary to a formatted string
        formatted_feedback = ""
        for section, details in feedback_info.items():
            if isinstance(details, dict) and "feedback" in details:
                formatted_feedback += f"\n{section.title()}\n"
                formatted_feedback += f"{details['feedback']}\n"
                
                if "example" in details:
                    if section == "work_experience":
                        formatted_feedback += format_work_experience(details["example"])
                    else:
                        if isinstance(details["example"], list):
                            for example in details["example"]:
                                formatted_feedback += f"- {example}\n"
                        else:
                            formatted_feedback += f"- {details['example']}\n"
                
                formatted_feedback += "\n"
        
        # Check if feedback is empty
        if not formatted_feedback:
            print("No feedback found. Cannot create email body.")
            return None
        
        # Combine opening, feedback, and closing
        formatted_email_body = f"{opening}\n{formatted_feedback}\n{closing}"
        
        # Create the draft
        draft = send_feedback_email_2(user_email, user_name, formatted_email_body)
        if draft:
            print(f"Initial draft created for {user_name}")
        else:
            print("Failed to create initial draft")
            
        return formatted_email_body
        
    except Exception as e:
        print(f"An error occurred when creating the email body: {str(e)}")
        print(f"Raw response: {resume_feedback}")
        print(f"Traceback: {traceback.format_exc()}")
        return None

def email_body_creation_with_df(candidate_id):
    """ Create email body using candidate data from dataframes and feedback results. Args: candidate_id (str): The ID of the candidate, Returns: str: Formatted email body or None if an error occurs"""
    try:
        # Get the candidate feedback using the new function
        feedback_result = get_candidate_feedback(candidate_id)
        
        # Check if feedback exists
        if not feedback_result:
            print(f"No feedback found for candidate {candidate_id}. Cannot create email body.")
            return None
        
        # Load the candidates dataframe
        try:
            candidates_df = pd.read_csv("data/processed_resumes/candidates.csv")
        except FileNotFoundError:
            print("Candidates dataframe not found")
            return None
            
        # Get candidate data
        candidate_data = candidates_df[candidates_df['candidate_id'] == candidate_id]
        if candidate_data.empty:
            print(f"Candidate with ID {candidate_id} not found")
            return None
            
        # Getting user info for email
        user_name = candidate_data['first_name'].iloc[0].title()
        user_email = candidate_data['email'].iloc[0]
        
        # Create the email body
        opening = f"Hola {user_name},\nRevisé tu CV a detalle y tengo algunas observaciones."
        closing = f"Esas son mis observaciones {user_name}, espero que sean de ayuda."
        
        # Process the feedback - assuming the structure is similar but from our flattened feedback
        formatted_feedback = ""
        
        # Check if the feedback contains the expected structure
        if 'feedback_json' in feedback_result:
            import json
            # If feedback is stored as a JSON string, parse it
            try:
                feedback_info = json.loads(feedback_result['feedback_json'])
                sections = feedback_info.get("general_feedback", {}).get("sections", {})
                
                for section, details in sections.items():
                    if isinstance(details, dict) and "feedback" in details:
                        formatted_feedback += f"\n{section.title()}\n"
                        formatted_feedback += f"{details['feedback']}\n"
                        
                        if "example" in details:
                            if section == "work_experience":
                                formatted_feedback += format_work_experience(details["example"])
                            else:
                                if isinstance(details["example"], list):
                                    for example in details["example"]:
                                        formatted_feedback += f"- {example}\n"
                                else:
                                    formatted_feedback += f"- {details['example']}\n"
                        formatted_feedback += "\n"
            except json.JSONDecodeError:
                print("Error decoding feedback JSON")
                return None
        else:
            # Alternative approach if feedback structure is different
            # Add logic to extract relevant feedback from the flattened structure
            sections = ['summary', 'hard_skills', 'soft_skills', 'work_experience', 'education']
            for section in sections:
                section_key = f"{section}_feedback"
                if section_key in feedback_result and feedback_result[section_key]:
                    formatted_feedback += f"\n{section.title()}\n"
                    formatted_feedback += f"{feedback_result[section_key]}\n\n"
                    formatted_feedback += f"Ejemplo:\n"
                    
                # Handle examples if they exist in this format
                example_key = f"{section}_example"
                if example_key in feedback_result and feedback_result[example_key]:
                    if section == "work_experience":
                        formatted_feedback += format_work_experience(feedback_result[example_key])
                    else:
                        examples = feedback_result[example_key]
                        if isinstance(examples, str):
                            examples = [e.strip() for e in examples.split(',')]
                        if isinstance(examples, list):
                            for example in examples:
                                formatted_feedback += f"- {example}\n"
                        else:
                            formatted_feedback += f"- {examples}\n"
                    formatted_feedback += "\n"
        
        # Check if feedback is empty
        if not formatted_feedback:
            print("No formatted feedback generated. Cannot create email body.")
            return None
            
        # Combine opening, feedback, and closing
        formatted_email_body = f"{opening}\n{formatted_feedback}\n{closing}"
        
        # Create the draft email
        draft, draft_id, draft_message_id, draft_message_thread_id, draft_message_label_id = send_feedback_email_2(user_email, user_name, formatted_email_body)
        if draft:
            print(f"Initial draft created for {user_name}")
            # Log the email sending in a CSV file
            log_email_sent(candidate_id, user_email, formatted_email_body, draft_id, draft_message_id, draft_message_thread_id, draft_message_label_id)
        else:
            print("Failed to create initial draft")
            
        return formatted_email_body
        
    except Exception as e:
        print(f"An error occurred when creating the email body: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return None

def format_work_experience(examples):
    """Format work experience examples for the email
    
    Args:
        examples (list or dict): Work experience examples
        
    Returns:
        str: Formatted work experience examples
    """
    formatted_text = ""
    
    if isinstance(examples, list):
        for example in examples:
            if isinstance(example, dict):
                job_title = example.get("job_title", "")
                company = example.get("company", "")
                formatted_text += f"- {job_title} at {company}\n"
            else:
                formatted_text += f"- {example}\n"
    elif isinstance(examples, dict):
        job_title = examples.get("job_title", "")
        company = examples.get("company", "")
        formatted_text += f"- {job_title} at {company}\n"
    else:
        formatted_text += f"- {examples}\n"
        
    return formatted_text

def email_body_creation_asking_questions(resume_array, questions):
    """Helper function to create a readable email body.
    Args: resume_array (dict): The whole dictionary containing the resume's data.
        questions (dict): The asked questions structured in a dictionary.
    Returns:
        tuple: A tuple containing the formatted email body, user's first name, and user's email."""
    try:
         # Check if questions is valid
        if not questions or "error" in questions:
            print("Invalid or empty questions dictionary. Cannot create email body.")
            return None, None, None
        
        # Extract user infomation
        user_first_name = resume_array["extracted_sections"]["user_info"]["first_name"].title()
        user_email = resume_array["extracted_sections"]["user_info"]["email"]

        # Create the email body
        opening = f"Hola {user_first_name},\nRevisé tu CV y tengo algunas preguntas para obtener información complementaria y generar una versión mejorada de tu CV. Por favor incluye toda la información que tengas, entre más información de valor, mejor. Dividí mis preguntas por sección y son las siguientes:"
        closing = f"Esas fueron mis preguntas {user_first_name}, se que son varias pero son muy importantes para generar una versión que resalte tus habilidades y así, resulte atractiva para los reclutadores. Quedamos atentos de tus respuestas\nIván Anaya y Marco García"

        # Extract the complementary info (nested dictionary)
        complementary_info = questions.get("asking_complementary_info", {})

        # Convert the questions dictionary to a formatted string
        formatted_questions = ""
        for section, details in complementary_info.items():
            if isinstance(details, dict) and "questions" in details:
                formatted_questions += f"{section.title()}\n"
                for i, question in enumerate(details["questions"], 1):
                    formatted_questions += f"{i}. {question}\n"
                formatted_questions += "\n"  # Add space between sections

        # Combine opening, questions, and closing
        formatted_email_body = f"{opening}\n\n{formatted_questions}\n{closing}"

        return formatted_email_body, user_first_name, user_email
    
    except Exception as e:
        print(f"An error ocurred when creating the email body from the list 'questions': {e}")
        return None

def format_feedback_content(feedback_dict):
    """Formats the feedback dictionary into a readable email body text."""
    email_content = []
    
    # Add email intro
    email_content.append(feedback_dict['email_intro'])
    email_content.append("\n")
    
    # Add each section's feedback
    for section, content in feedback_dict['sections'].items():
         # Section header
        email_content.append(f" {section.replace('_', ' ').title()} \n")
        
        # Add feedback
        email_content.append("Retroalimentación:")
        # Clean up the feedback text by removing markdown if present
        feedback_text = content['feedback']
        feedback_text = feedback_text.replace('**', '').replace('*', '•')
        email_content.append(feedback_text)
        email_content.append("\n")

        # Add example
        email_content.append("Ejemplo:")
        # If example is a dictionary or list, format it for readability
        example = content['example']
        if isinstance(example, (dict, list)) or str(example).strip().startswith('{') or str(example).strip().startswith('['):
            # Convert string representation of dict/list to actual object if needed
            if isinstance(example, str):
                try:
                    import ast
                    example = ast.literal_eval(example)
                except:
                    pass
            if isinstance(example, (dict, list)):
                # Format dictionaries and lists in a readable way
                formatted_example = format_structured_data(example)
            else:
                formatted_example = example
        else:
            formatted_example = example
            
        email_content.append(formatted_example)
        email_content.append("\n")

    # Add closing message
    email_content.append(feedback_dict['closing'])
    
    # Join all parts with proper spacing
    return "\n".join(email_content)

def format_structured_data(data, indent=0):
    """Helper function to format dictionaries and lists in a readable way."""
    if isinstance(data, dict):
        formatted = []
        for key, value in data.items():
            key_str = key.replace('_', ' ').title()
            if isinstance(value, (dict, list)):
                formatted.append(f"{'  ' * indent}{key_str}:")
                formatted.append(format_structured_data(value, indent + 1))
            else:
                formatted.append(f"{'  ' * indent}{key_str}: {value}")
        return '\n'.join(formatted)
    elif isinstance(data, list):
        formatted = []
        for item in data:
            if isinstance(item, (dict, list)):
                formatted.append(format_structured_data(item, indent + 1))
            else:
                formatted.append(f"{'  ' * indent}• {item}")
        return '\n'.join(formatted)
    else:
        return str(data)
    
def format_feedback_content_API_call(feedback):
    """Helper function to extract the feedback from the json or dictionary and set it into a easy to read email with an API call"""
    try:
        feedback_email_format = ""
        prompt_content = load_prompt("email_format_generator_v1.txt")
        formatted_prompt = prompt_content.format(json_api_response = feedback)

        feedback_email_format = gemini_api.generate_content(formatted_prompt)
        return feedback_email_format
    except Exception as e:
        print(f"An error ocurred when formating the responso into an email body: {e}")
        return None
    

