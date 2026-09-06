import logging.config
import base64
import email
import json
import os
import traceback
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

# Global variable used for logging
log = None

# Global variable used for the configuration
config = {}

# Absolute path of the script directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Absolute path of the configuration file
conf_file_path = os.path.join(script_dir, "..", "..", "conf", "configuration.json")

# Absolute path of the logging configuration file
log_conf_file_path = os.path.join(script_dir, "..", "..", "conf", "logging_conf.json")

# Absolute path of the token file
token_file_path = os.path.join(script_dir, "..", "..", "conf", "gmail_token.json")

# Absolute path of the output JSON file
output_file_path = os.path.join(script_dir, "..", "..", "output", "emails.json")

# Normalize the relative paths to obtain the correct absolute paths
token_file_path = os.path.normpath(token_file_path)
output_file_path = os.path.normpath(output_file_path)


def connect_to_Gmail_API():
    creds = None

    if os.path.exists(token_file_path):
        creds = Credentials.from_authorized_user_file(token_file_path)

    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_file_path, "w") as token_file:
                token_file.write(creds.to_json())
        else:
            creds = None

    if not creds:
        # Load the raw JSON string from the environment variable
        client_config = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

        # Use from_client_config instead of a file path
        flow = InstalledAppFlow.from_client_config(
            client_config,
            [
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.send",
            ],
        )
        creds = flow.run_local_server(port=8000)

        with open(token_file_path, "w") as token_file:
            token_file.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


# Fetch all the unread emails in the specified folder that have an EML attachment and save their information to a JSON file
def retrieve_emails(service):
    # Get a list of unread emails from the specified folder
    results = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], q="is:unread")
        .execute()
    )
    messages = results.get("messages", [])
    new_emails = len(messages)
    log.info("{} unread messages to process".format(new_emails))

    # Variable that will contain the information related to the unread emails
    emails_info = []

    for message in messages:
        msg = service.users().messages().get(userId="me", id=message["id"]).execute()

        # Mark the email as read
        # service.users().messages().modify(userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()

        # Extract the required fields from the email
        headers = msg["payload"]["headers"]
        subject = get_header_value(headers, "Subject")
        sender = get_header_value(headers, "From")
        log.info("Message from: {0} with subject: {1}".format(sender, subject))

        # Get the email body
        body = get_email_body(msg)

        # Check if there is an EML attachment
        eml_attachment_found, attached_mail_subject = find_eml_attachment(msg, service)

        # Add email information to the list
        email_info = {
            "mailUID": message["id"],
            "from": sender,
            "subject": subject,
            "date": msg["internalDate"],
        }

        emails_info.append(email_info)

    # Save the emails information to the output JSON file
    with open(output_file_path, "w") as output_file:
        json.dump(emails_info, output_file)

    log.info("Emails information saved to {}".format(output_file_path))


# Utility function to get the value of a specific header from a list of headers
def get_header_value(headers, header_name):
    for header in headers:
        if header["name"] == header_name:
            return header["value"]
    return None


# Utility function to get the body of an email
def get_email_body(msg):
    body = None

    for part in msg["payload"]["parts"]:
        if "data" in part["body"]:
            data = part["body"]["data"]
            if part["mimeType"] == "text/plain":
                body = base64.urlsafe_b64decode(data).decode("utf-8")
                break
        elif "parts" in part:
            for subpart in part["parts"]:
                if subpart["mimeType"] == "text/plain":
                    data = subpart["body"]["data"]
                    body = base64.urlsafe_b64decode(data).decode("utf-8")
                    break

    return body


# Utility function to find an EML attachment in an email
def find_eml_attachment(msg, service):
    eml_attachment_found = False
    attached_mail_subject = ""

    def search_eml_attachment(part):
        nonlocal eml_attachment_found, attached_mail_subject

        if part.get("mimeType") == "message/rfc822":
            eml_payload = part.get("body", {}).get("attachmentId")
            if eml_payload:
                attachment = (
                    service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=msg["id"], id=eml_payload)
                    .execute()
                )
                data = attachment["data"]
                eml_payload = base64.urlsafe_b64decode(data).decode()
                internal_msg = email.message_from_string(eml_payload)
                attached_mail_subject = internal_msg["Subject"]
                eml_attachment_found = True
        elif part.get("parts"):
            for subpart in part["parts"]:
                search_eml_attachment(subpart)

    if "payload" in msg and "parts" in msg["payload"]:
        for part in msg["payload"]["parts"]:
            search_eml_attachment(part)

    return eml_attachment_found, attached_mail_subject


# Main function called from outside
def main():
    global config
    global log
    global conf_file_path
    global log_conf_file_path

    # Logging configuration
    try:
        with open(log_conf_file_path) as log_conf:
            log_conf_dict = json.load(log_conf)
            logging.config.dictConfig(log_conf_dict)
    except Exception as e:
        print(
            "[ERROR]_[list_emails]: Error while trying to open the file 'logging_conf.json'. It cannot be read or it is not valid: {}".format(
                traceback.format_exc()
            )
        )
        return
    log = logging.getLogger(__name__)

    # IMAP configuration
    try:
        with open(conf_file_path) as conf_file:
            conf_dict = json.load(conf_file)

    except Exception as e:
        log.error(
            "Error while trying to open the file 'configuration.json': {}".format(
                traceback.format_exc()
            )
        )
        return

    # Connect to Gmail API
    try:
        service = connect_to_Gmail_API()
    except Exception as e:
        log.error(
            "Error while trying to connect to Gmail API: {}".format(
                traceback.format_exc()
            )
        )
        return

    # Call the retrieve_emails function
    try:
        retrieve_emails(service)
    except Exception as e:
        log.error(
            "Error while trying to retrieve the emails: {}".format(
                traceback.format_exc()
            )
        )
        return


if __name__ == "__main__":
    main()
