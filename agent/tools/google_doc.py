#agent/tools/google_doc.py
import time
import re
import os
import uuid
import asyncio
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from integration.google.drive_api import get_google_api_credentials, build_google_service


def _format_work_experience_requests(example_text: str, start_index: int) -> tuple[list, int]:
    """
    Parses work experience example text and generates Docs API requests
    for specific formatting (bold title, bullet points).

    Args:
        example_text (str): The example text for work experience, expected in
                            "[Title Info], [description: Point 1. Point 2...]" format.
        start_index (int): The starting index in the Google Doc for inserting content.

    Returns:
        tuple[list, int]: A tuple containing:
                          - A list of Google Docs API request objects.
                          - The updated index after adding the content.
    """
    requests = []
    current_index = start_index
    fallback_requests = []

    # Fallback content in case parsing fails
    fallback_content = f"Example:\n{example_text}\n\n"
    fallback_requests.append({'insertText': {'location': {'index': current_index}, 'text': fallback_content}})
    fallback_index = current_index + len(fallback_content)

    try:
        # --- 1. Add "Example:" Label ---
        example_label = "Example:\n"
        requests.append({'insertText': {'location': {'index': current_index}, 'text': example_label}})
        current_index += len(example_label)

        # --- 2. Parse Title and Description ---
        # Using regex for slightly more robust parsing than simple split
        # It looks for "[...], [description: ...]"
        match = re.match(r"^\s*\[(.*?)\]\s*,\s*\[description:\s*(.*)\]\s*$", example_text, re.DOTALL)

        if not match:
            print(f"Warning: Could not parse work experience example format: {example_text}. Using fallback.")
            # Return the fallback requests if parsing fails
            return fallback_requests, fallback_index

        title_part = match.group(1).strip()
        description_part = match.group(2).strip()

        # --- 3. Insert and Format Title ---
        title_text = f"{title_part}\n"
        title_start_index = current_index
        requests.append({'insertText': {'location': {'index': title_start_index}, 'text': title_text}})
        # Apply bold style to the title text (excluding the newline)
        requests.append({'updateTextStyle': {
            'range': {'startIndex': title_start_index, 'endIndex': title_start_index + len(title_text) - 1},
            'textStyle': {'bold': True},
            'fields': 'bold' # Specify only the fields you want to update
        }})
        current_index += len(title_text) # Update index *after* insertion

        # --- 4. Insert Description as Bullet Points ---
        # Attempt to split description into points. This is still fragile.
        # Assumes points are separated by ". " followed by a capital letter, or are distinct sentences.
        # A more robust solution involves structuring the input data better (e.g., a list of strings).
        # Split by common sentence endings followed by space, keeping the delimiter.
        # This regex splits after a period, question mark, or exclamation mark followed by a space.
        bullet_points = re.split(r'(?<=[.?!])\s+', description_part)
        # Filter out any empty strings that might result from splitting
        bullet_points = [p.strip() for p in bullet_points if p.strip()]


        if bullet_points:
            bullet_start_index = current_index
            for point in bullet_points:
                point_text = f"{point}\n" # Add newline to make it a paragraph
                requests.append({'insertText': {'location': {'index': current_index}, 'text': point_text}})
                current_index += len(point_text)
            bullet_end_index = current_index

            # Apply bullet points to the paragraphs we just inserted
            # The range covers the entire block of bullet points.
            requests.append({'createParagraphBullets': {
                'range': {
                    'startIndex': bullet_start_index,
                    'endIndex': bullet_end_index # End index is exclusive
                },
                'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE' # Standard bullet style
            }})
            # Add an extra newline for spacing after the bullets
            requests.append({'insertText': {'location': {'index': current_index}, 'text': '\n'}})
            current_index += 1

        else:
            # If splitting fails, insert the description part as plain text
            print(f"Warning: Could not split description into bullet points: {description_part}. Inserting as plain text.")
            desc_text = f"{description_part}\n\n"
            requests.append({'insertText': {'location': {'index': current_index}, 'text': desc_text}})
            current_index += len(desc_text)


        return requests, current_index

    except Exception as e:
        print(f"Error during work experience formatting: {e}. Using fallback.")
        # Return the fallback requests in case of any unexpected error
        return fallback_requests, fallback_index


async def create_google_doc(user_id: str, feedback_data: dict, doc_purpose: str = "Reporte_de_retroalimentación v1") -> str | None:
        """
        Creates a Google Doc, populates it with formatted feedback, and returns the URL.
        Includes special formatting for the work experience section.

        Uses service account credentials suitable for Cloud Run.

        Args:
            user_id (str): The ID of the user for whom the feedback is generated.
            feedback_data (dict): The dictionary containing feedback sections
                                    (e.g., summary, hard_skills) with 'feedback' and 'example'.
            doc_purpose (str): A string describing the purpose of the document (used in title).

        Returns:
            str | None: The URL (webViewLink) of the created Google Doc, or None if creation failed.
        """
        print(f"Initiating Google Doc creation for user: {user_id}, purpose: {doc_purpose}")

        try:
            # --- 1. Get Credentials and Build Services (using asyncio.to_thread) ---
            # Use asyncio.to_thread since the underlying google auth/build calls are synchronous
            creds = await asyncio.to_thread(get_google_api_credentials)
            drive_service = await asyncio.to_thread(build_google_service, 'drive', 'v3', creds)
            docs_service = await asyncio.to_thread(build_google_service, 'docs', 'v1', creds)
            print("Successfully built Drive and Docs API services.")

            # --- 2. Define Document Title ---
            # Create a unique and descriptive title
            doc_title = f"{doc_purpose} - User {user_id} - {uuid.uuid4().hex[:8]}"
            print(f"Document Title: {doc_title}")

            # --- 3. Create Blank Google Doc using Drive API ---
            file_metadata = {
                'name': doc_title,
                'mimeType': 'application/vnd.google-apps.document',
                'parents': [os.getenv('GOOGLE_DRIVE_FEEDBACK_FOLDER_ID')] # Folder ID to store the doc
            }

            print("Creating Google Doc file via Drive API...")
            # Run synchronous API call in thread pool
            file = await asyncio.to_thread(
                drive_service.files().create(
                    body=file_metadata,
                    fields='id, webViewLink' # Request ID and URL
                ).execute
            )

            doc_id = file.get('id')
            doc_url = file.get('webViewLink')
            if not doc_id:
                print(f"Error: Failed to create Google Doc file. No ID returned.")
                return None
            print(f"Successfully created Google Doc file. ID: {doc_id}, URL: {doc_url}")


            # --- 4. Format Content for Docs API ---
            requests = []
            current_index = 1 # Docs API uses 1-based indexing for content

            # --- Document Title ---
            doc_main_title = "Retroalimentación de tu CV\n"
            requests.append({'insertText': {'location': {'index': current_index}, 'text': doc_main_title}})
            requests.append({'updateParagraphStyle': {
                'range': {'startIndex': current_index, 'endIndex': current_index + len(doc_main_title)},
                'paragraphStyle': {'namedStyleType': 'TITLE'},
                'fields': 'namedStyleType'}})
            current_index += len(doc_main_title)

            # --- Sections ---
            # Define standard section order (optional, but good for consistency)
            section_order = ["summary", "hard_skills", "soft_skills", "work_experience", "education", "languages"]

            # Iterate through sections in defined order, skipping if not present in data
            for section_key in section_order:
                if section_key not in feedback_data:
                    continue # Skip section if no data provided

                section_value = feedback_data[section_key]
                # Safely get feedback and example text
                feedback_text = section_value.get("feedback", "").strip() if section_value else ""
                example_text = section_value.get("example", "").strip() if section_value else ""

                # Skip section entirely if both feedback and example are empty
                if not feedback_text and not example_text:
                    continue

                # --- Section Title ---
                title = section_key.replace('_', ' ').title()
                # Add section heading (e.g., "Summary", "Hard Skills")
                section_title_text = f"{title}\n"
                requests.append({'insertText': {'location': {'index': current_index}, 'text': section_title_text}})
                # Apply Heading 1 style
                requests.append({'updateParagraphStyle': {
                    'range': {'startIndex': current_index, 'endIndex': current_index + len(section_title_text)},
                    'paragraphStyle': {'namedStyleType': 'HEADING_1'},
                    'fields': 'namedStyleType'}})
                current_index += len(section_title_text)

                # --- Feedback Text ---
                if feedback_text:
                    feedback_content = f"Feedback:\n{feedback_text}\n\n" # Add label and spacing
                    requests.append({'insertText': {'location': {'index': current_index}, 'text': feedback_content}})
                    current_index += len(feedback_content)

                # --- Example Text (Conditional Formatting) ---
                if example_text:
                    if section_key == "work_experience":
                        # Use the helper function for special formatting
                        print(f"Formatting work experience example for section: {section_key}")
                        wx_requests, updated_index = _format_work_experience_requests(example_text, current_index)
                        requests.extend(wx_requests)
                        current_index = updated_index
                    else:
                        # Standard formatting for other sections
                        print(f"Formatting standard example for section: {section_key}")
                        example_content = f"Example:\n{example_text}\n\n"
                        requests.append({'insertText': {'location': {'index': current_index}, 'text': example_content}})
                        current_index += len(example_content)

                    #example_content = f"Example:\n{example_text}\n\n" # Add label and spacing
                    #requests.append({'insertText': {'location': {'index': current_index}, 'text': example_content}})
                    #current_index += len(example_content)

            print(f"Prepared {len(requests)} requests for Docs API batchUpdate.")

            # --- 5. Populate the Document using Docs API ---
            if requests:
                print(f"Populating Google Doc (ID: {doc_id}) via Docs API batchUpdate...")
                # Run synchronous API call in thread pool
                await asyncio.to_thread(
                    docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': requests}
                    ).execute
                )
                print(f"Successfully populated Google Doc (ID: {doc_id}).")
            else:
                print(f"Warning: No content generated from feedback_data for Doc ID: {doc_id}. Document remains blank.")

            # --- 6. Return Document URL ---
            return doc_url

        except HttpError as error:
            # Handle API errors specifically
            error_details = error.resp.get('content', '{}') # Get error content if available
            print(f"An Google API error occurred: {error}")
            print(f"Error details: {error_details}")
            # Consider deleting the potentially empty file created if population failed? Optional.
            return None
        except FileNotFoundError as fnf_error:
            # Handle missing service account key file
            print(f"Authentication Error: {fnf_error}")
            return None
        except ValueError as val_error:
            # Handle missing environment variable
            print(f"Configuration Error: {val_error}")
            return None
        except Exception as e:
            # Handle other unexpected errors
            print(f"An unexpected error occurred during Google Doc creation: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging
            return None