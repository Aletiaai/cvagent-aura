# Purpose: Encapsulate email reading/searching logic (if needed for triggers).


def get_label_id(label_name):
    """Gets the ID of a label by its name.
        Args: label_name: The name of the label.
        Returns:The label ID (or None if not found).
    """
    try:
        results = service.users().labels().list(userId = 'me').execute()
        labels = results.get('labels', [])

        for label in labels:
            if label['name'] == label_name:
                return label['id']

        return None  # Label not found
    except Exception as e:
        print(f'An error occurred: {e}')
        return None

def search_emails(label_ids = None):
    """Searches for emails matching the given query.
    Args: query: The search query (optional).
         label_ids: A list of label IDs to filter by .
    Returns: A list of email message IDs.
    """
    try:
        response = service.users().messages().list(userId = 'me', labelIds=label_ids).execute()
        messages = []
        if 'messages' in response:
            messages.extend(response['messages'])
        
        while 'nextPageToken' in response:
            page_token = response ['nextPageToken']
            response = service.users().messages().list(userId = 'me', labelIds=label_ids, pageToken = page_token).execute()
            messages.extend(response['messages'])

        return [msg['id'] for msg in messages]
    except Exception as e:
        print[f'An error occurred:{e}']
        return[]

def get_message(msg_id):
    """Get a specific email message.
    Args:service: The gmail api service object.
        msg_id: The ID of the message to retrieve.
    Returns:The message object (or none if an error ocurrs)"""
    
    try:
        message = service.users().messages().get(userId = 'me', id = msg_id, format = 'raw').execute()
        #Decode the raw message
        msg_raw = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
        msg_str = email.message_from_bytes(msg_raw, _class = EmailMessage)

        return msg_str
    except Exception as e:
        print(f'An error ocurred {e}')
        return None

def get_attachments(msg_id, download_dir = "user_resumes"):
    """Downloads attachments from a specific email message.
    Args:service: The Gmail API service object.
        msg_id: The ID of the message containing the attachments.
        download_dir: The directory to save the attachments (default: "user_resumes")."""
    try:
        message = service.users().messages().get(userId = 'me', id = msg_id).execute()
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        for part in message['payload']['parts']:
            if part['filename']:
                if 'data' in part['body']:
                    data = part['body']['data']
                else:
                    att_id = part['body']['attachmentId']
                    att = service.users().messages().attachments().get(userId = 'me', messageId = msg_id, id = att_id).execute()
                    data = att['data']
                file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                filepath = os.path.join(download_dir, part['filename'])

                with open(filepath, 'wb') as f:
                    f.write(file_data)
                print(f"Attachment saved to: {filepath}")

    except Exception as e:
        print(f'An error occurred: {e}')

# These also need the Gmail service object.
