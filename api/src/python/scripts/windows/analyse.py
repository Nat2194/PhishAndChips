import sys
import logging.config
import io
import json
import base64
import hashlib
import re
import time
import email
import emoji
import urllib.parse
import traceback
import ioc_finder
import thehive4py.api, thehive4py.models, thehive4py.query
import cortex4py.api
import socketio
import json
import os
import traceback
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# Global variable used for logging
log = None

# Global variable needed to use the API
api_thehive = None
api_cortex = None

# Global variable used for the configuration
config = {}

# Global variable used for the whitelist
whitelist = {}

# Absolute path of the script directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Absolute path of the configuration file
conf_file_path = os.path.join(script_dir, "..", "..", "conf", "configuration.json")

# Absolute path of the logging configuration file
log_conf_file_path = os.path.join(script_dir, "..", "..", "conf", "logging_conf.json")

# Absolute path of the analyzers level configuration file
analyzers_conf_file_path = os.path.join(
    script_dir, "..", "..", "conf", "analyzers_level_conf.json"
)

# Absolute path of the whitelist file
whitelist_file_path = os.path.join(script_dir, "..", "..", "conf", "whitelist.json")

# Absolute path of the OAuth 2.0 key file
key_file_path = os.path.join(script_dir, "..", "..", "conf", "gmail_key.json")

# Absolute path of the token file
token_file_path = os.path.join(script_dir, "..", "..", "conf", "gmail_token.json")


# Normalize the relative paths to obtain the correct absolute paths
key_file_path = os.path.normpath(key_file_path)
token_file_path = os.path.normpath(token_file_path)
analyzers_conf_file_path = os.path.normpath(analyzers_conf_file_path)
whitelist_file_path = os.path.normpath(whitelist_file_path)


# Detects if there is already a case being processed
def is_output_file_empty(file_path):
    return os.path.isfile(file_path) and os.stat(file_path).st_size != 0


# Check if an observable is whitelisted with an exact match or with a regex match
def is_whitelisted(obs_type, obs_value):
    found = False
    if (not found) and (obs_value in whitelist[obs_type + "Exact"]):
        found = True
    if (not found) and (obs_type == "domain"):
        for regex in whitelist["regexDomainsInSubdomains"]:
            if re.search(regex, obs_value):
                found = True
    if (not found) and (obs_type == "url"):
        for regex in whitelist["regexDomainsInURLs"]:
            if re.search(regex, obs_value):
                found = True
    if (not found) and (obs_type == "mail"):
        for regex in whitelist["regexDomainsInEmails"]:
            if re.search(regex, obs_value):
                found = True
    if (not found) and (obs_type not in ["hash", "filetype"]):
        for regex in whitelist[obs_type + "Regex"]:
            if re.search(regex, obs_value):
                found = True
    return found


# Establishing a connection to Gmail API and creating a token
def connect_to_Gmail_API(sio):
    # Load credentials from token file if it exists
    creds = None
    if os.path.exists(token_file_path):
        creds = Credentials.from_authorized_user_file(token_file_path)

    # If credentials are not valid, authenticate and generate new token
    if creds and not creds.valid:
        creds.refresh(Request())

        # Save the refreshed credentials to the token file
        with open(token_file_path, "w") as token_file:
            token_file.write(creds.to_json())

    # If credentials do not exist, authenticate and generate new token
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            key_file_path,
            [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify",
            ],
            redirect_uri="http://localhost:8000/",
        )
        creds = flow.run_local_server(port=8000)

        # Save the credentials to the token file
        with open(token_file_path, "w") as token_file:
            token_file.write(creds.to_json())

    # Build the Gmail service
    service = build("gmail", "v1", credentials=creds)
    log.info("Connexion réussie à l'API Gmail")
    message = {"event": "satus", "data": "Connexion réussie à l'API Gmail"}
    sio.emit("status", json.dumps(message))

    return service


# Use the ioc-finder module to extract observables from a string buffer and add to the list
def search_observables(buffer):
    observables = []
    iocs = {}
    iocs["email_addresses"] = ioc_finder.parse_email_addresses(buffer)
    iocs["ipv4s"] = ioc_finder.parse_ipv4_addresses(buffer)
    iocs["domains"] = ioc_finder.parse_domain_names(buffer)
    # Option to parse URLs without a scheme (e.g. without https://)
    iocs["urls"] = ioc_finder.parse_urls(buffer, parse_urls_without_scheme=False)
    for mail in iocs["email_addresses"]:
        if is_whitelisted("mail", mail):
            log.info("Skipped whitelisted observable mail: {0}".format(mail))
        else:
            log.info("Found observable mail: {0}".format(mail))
            observables.append({"type": "mail", "value": mail})

    for ip in iocs["ipv4s"]:
        if is_whitelisted("ip", ip):
            log.info("Skipped whitelisted observable ip: {0}".format(ip))
        else:
            log.info("Found observable ip: {0}".format(ip))
            observables.append({"type": "ip", "value": ip})
    for domain in iocs["domains"]:
        if is_whitelisted("domain", domain):
            log.info("Skipped whitelisted observable domain: {0}".format(domain))
        else:
            log.info("Found observable domain: {0}".format(domain))
            observables.append({"type": "domain", "value": domain})
    for url in iocs["urls"]:
        if is_whitelisted("url", url):
            log.info("Skipped whitelisted observable url: {0}".format(url))
        else:
            log.info("Found observable url: {0}".format(url))
            observables.append({"type": "url", "value": url})
    return observables


# Use the mail UID of the selected email to fetch only that email from the mailbox
def obtain_eml(service, mail_uid, sio):
    logging.info(f"Obtaining email with ID: {mail_uid}")
    message = {
        "event": "status",
        "data": f"Récupération du mail correspondant à l'ID: {mail_uid}",
    }
    sio.emit("status", json.dumps(message))
    # Read the email using the Gmail API
    message = (
        service.users()
        .messages()
        .get(userId="me", id=mail_uid, format="full")
        .execute()
    )

    # Mark the email as read
    service.users().messages().modify(
        userId="me", id=message["id"], body={"removeLabelIds": ["UNREAD"]}
    ).execute()

    # Obtain the From field of the external email that will be used to send the verdict to the user

    for header in message["payload"]["headers"]:
        if header["name"] == "From":
            external_from_field = header["value"]
            break
    else:
        external_from_field = None
    parsed_from_field = email.utils.parseaddr(external_from_field)
    if len(parsed_from_field) > 1:
        external_from_field = parsed_from_field[1]

    # Variable used to detect the mimetype of the email parts
    mimetype = None

    # Variable that will contain the internal EML file
    internal_msg = None

    # Walk the multipart structure of the email (now only the EML part is needed)
    for part in message["payload"]["parts"]:
        if "body" in part:
            mimetype = part["mimeType"]
            if mimetype in ["application/octet-stream", "message/rfc822"]:
                eml_payload = part.get("body", {}).get("attachmentId")
                if eml_payload:
                    attachment = (
                        service.users()
                        .messages()
                        .attachments()
                        .get(userId="me", messageId=mail_uid, id=eml_payload)
                        .execute()
                    )
                    eml_data = base64.urlsafe_b64decode(attachment["data"])
                    internal_msg = email.message_from_bytes(eml_data)
                else:
                    internal_msg = None
                break

    message = {
        "event": "status",
        "data": f"Mail récupéré : {mail_uid}",
    }
    sio.emit("status", json.dumps(message))
    return internal_msg, external_from_field


# Parse the EML file and extract the observables
def parse_eml(internal_msg, sio):
    # Obtain the subject of the internal email
    # This is not straightforward since the subject might be splitted in two or more parts
    decode_subj = email.header.decode_header(internal_msg["Subject"])
    decoded_elements_subj = []
    for decode_elem in decode_subj:
        if decode_elem[1] is not None:
            if str(decode_elem[1]) == "unknown-8bit":
                decoded_elements_subj.append(decode_elem[0].decode())
            else:
                decoded_elements_subj.append(decode_elem[0].decode(decode_elem[1]))
        else:
            if isinstance(decode_elem[0], str):
                decoded_elements_subj.append(str(decode_elem[0]))
            else:
                decoded_elements_subj.append(decode_elem[0].decode())
        subject_field = "".join(decoded_elements_subj)

    log.info("Analyzing attached message with subject: {}".format(subject_field))

    # List of attachments of the internal email
    attachments = []

    # List of attachment hashes
    hashes_attachments = []

    # List of observables found in the body of the internal email
    observables_body = []

    # Dictionary containing a list of observables found in each header field
    observables_header = {}

    # List of header fields to consider when searching for observables in the header
    header_fields_list = [
        "To",
        "From",
        "Sender",
        "Cc",
        "Delivered-To",
        "Return-Path",
        "Reply-To",
        "Bounces-to",
        "Received",
        "X-Received",
        "X-OriginatorOrg",
        "X-Sender-IP",
        "X-Originating-IP",
        "X-SenderIP",
        "X-Originating-Email",
    ]

    # Extract header fields
    parser = email.parser.HeaderParser()
    header_fields = parser.parsestr(internal_msg.as_string())

    # Search the observables in the values of all the selected header fields
    # Since a field may appear more than one time (e.g. Received:), the lists need to be initialized and then extended
    i = 0
    while i < len(header_fields.keys()):
        if header_fields.keys()[i] in header_fields_list:
            if not observables_header.get(header_fields.keys()[i]):
                observables_header[header_fields.keys()[i]] = []
            observables_header[header_fields.keys()[i]].extend(
                search_observables(header_fields.values()[i])
            )
        i += 1

    # Walk the multipart structure of the internal email
    for part in internal_msg.walk():
        mimetype = part.get_content_type()
        content_disposition = part.get_content_disposition()
        if content_disposition != "attachment":
            # Extract the observables from the body (from both text/plain and text/html parts) using the search_observables function
            if mimetype == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode()
                except UnicodeDecodeError:
                    body = part.get_payload(decode=True).decode("ISO-8859-1")
                observables_body.extend(search_observables(body))
            elif mimetype == "text/html":
                try:
                    html = part.get_payload(decode=True).decode()
                except UnicodeDecodeError:
                    html = part.get_payload(decode=True).decode("ISO-8859-1")
                # Handle URL encoding
                html_urldecoded = urllib.parse.unquote(html.replace("&amp;", "&"))
                observables_body.extend(search_observables(html_urldecoded))
        # Extract attachments
        else:
            filename = part.get_filename()
            if filename and mimetype:
                if is_whitelisted("filename", filename) or is_whitelisted(
                    "filetype", mimetype
                ):
                    log.info(
                        "Skipped whitelisted observable file: {0}".format(filename)
                    )
                    message = {
                        "event": "satus",
                        "data": "Elément observable de la whiteliste passé: {0}".format(
                            filename
                        ),
                    }
                    sio.emit("status", json.dumps(message))
                else:
                    # Add the attachment
                    inmem_file = io.BytesIO(part.get_payload(decode=1))
                    attachments.append((inmem_file, filename))
                    log.info("Found observable file: {0}".format(filename))
                    message = {
                        "event": "satus",
                        "data": "Elément observable trouvé: {0}".format(filename),
                    }
                    sio.emit("status", json.dumps(message))
                    # Calculate the hash of the just found attachment
                    sha256 = hashlib.sha256()
                    sha256.update(part.get_payload(decode=1))
                    hash_attachment = {}
                    hash_attachment["hashValue"] = sha256.hexdigest()
                    hash_attachment["hashedAttachment"] = filename
                    if is_whitelisted("hash", hash_attachment["hashValue"]):
                        log.info(
                            "Skipped whitelisted observable hash: {0}".format(
                                hash_attachment["hashValue"]
                            )
                        )
                        message = {
                            "event": "satus",
                            "data": "Elément hash de la whiteliste passé: {0}".format(
                                hash_attachment["hashValue"]
                            ),
                        }
                        sio.emit("status", json.dumps(message))
                    else:
                        hashes_attachments.append(hash_attachment)
                        log.info(
                            "Found observable hash {0} calculated from file: {1}".format(
                                hash_attachment["hashValue"], filename
                            )
                        )
                        message = {
                            "event": "satus",
                            "data": "Hash {0} de l'élément {1} calculé".format(
                                hash_attachment["hashValue"], filename
                            ),
                        }
                        sio.emit("status", json.dumps(message))

    # Create a tuple containing the eml file and the name it should have as an observable
    filename = subject_field + ".eml"
    inmem_file = io.BytesIO()
    gen = email.generator.BytesGenerator(inmem_file)
    gen.flatten(internal_msg)
    eml_file_tuple = (inmem_file, filename)

    # Workaround to prevent HTML tags to appear inside the URLs (splits on < or >)
    for observable_body in observables_body:
        if observable_body["type"] == "url":
            observable_body["value"] = (
                observable_body["value"].replace(">", "<").split("<")[0]
            )

    return (
        subject_field,
        observables_header,
        observables_body,
        attachments,
        hashes_attachments,
        eml_file_tuple,
    )


# Create the case on TheHive and add the observables to it
def create_case(
    subject_field,
    observables_header,
    observables_body,
    attachments,
    hashes_attachments,
    eml_file_tuple,
    sio,
):
    # Create the case template first if it does not exist
    if (
        len(
            api_thehive.find_case_templates(
                query=thehive4py.query.Eq("name", "PhishAndChips")
            ).json()
        )
    ) == 0:
        task_notification = thehive4py.models.CaseTask(
            title="PhishAndChips notification"
        )
        task_analysis = thehive4py.models.CaseTask(title="PhishAndChips analysis")
        task_result = thehive4py.models.CaseTask(title="PhishAndChips result")
        case_template = thehive4py.models.CaseTemplate(
            name="PhishAndChips",
            titlePrefix="[PhishAndChips] ",
            tasks=[task_notification, task_analysis, task_result],
        )
        response = api_thehive.create_case_template(case_template)
        if response.status_code == 201:
            log.info("Template PhishAndChips created successfully")
            message = {"event": "satus", "data": "Template de cas PhishAndChips créée"}
            sio.emit("status", json.dumps(message))
        else:
            log.error(
                "Cannot create template: {0} ({1})".format(
                    response.status_code, response.text
                )
            )
            message = {
                "event": "satus",
                "data": "Erreur lors de la création de la template de cas PhishAndChips: {0} ({1})".format(
                    response.status_code, response.text
                ),
            }
            sio.emit("status", json.dumps(message))
            return

    # Create the case on TheHive
    # The emojis are removed to prevent problems when exporting the case to MISP
    case = thehive4py.models.Case(
        title=emoji.replace_emoji(subject_field),
        tlp=int(config["caseTLP"]),
        pap=int(config["casePAP"]),
        flag=False,
        tags=config["caseTags"],
        description="Case created automatically by PhishAndChips",
        template="PhishAndChips",
    )

    # Seems like the case template cannot be detected if we don't run a query to look for it before, hopefully this will be corrected and this part will become unnecessary

    log.info("case template")
    log.info(
        api_thehive.find_case_templates(
            query=thehive4py.query.Eq("name", "PhishAndChips")
        ).json()
    )

    response = api_thehive.create_case(case)
    if response.status_code == 201:
        new_case = response
        new_id = new_case.json()["id"]
        new_case_id = new_case.json()["caseId"]
        log.info("Created case {}".format(new_case_id))
        message = {"event": "satus", "data": "Cas créé: {}".format(new_case_id)}
        sio.emit("status", json.dumps(message))

        # Add observables found in the mail header
        for header_field in observables_header:
            for observable_header in observables_header[header_field]:
                observable = thehive4py.models.CaseObservable(
                    dataType=observable_header["type"],
                    data=observable_header["value"],
                    ioc=False,
                    tags=[
                        "email",
                        "email_header",
                        "email_header_{}".format(header_field),
                    ],
                    message="Found in the {} field of the email header".format(
                        header_field
                    ),
                )
                response = api_thehive.create_case_observable(new_id, observable)
                if response.status_code == 201:
                    log.info(
                        "Added observable {0}: {1} to case {2}".format(
                            observable_header["type"],
                            observable_header["value"],
                            new_case_id,
                        )
                    )
                    message = {
                        "event": "satus",
                        "data": "Observable {1} de type {0} ajouté au cas {2}".format(
                            observable_header["type"],
                            observable_header["value"],
                            new_case_id,
                        ),
                    }
                    sio.emit("status", json.dumps(message))
                else:
                    log.debug(
                        "Cannot add observable {0}: {1} - {2} ({3})".format(
                            observable_header["type"],
                            observable_header["value"],
                            response.status_code,
                            response.text,
                        )
                    )
                    message = {
                        "event": "satus",
                        "data": "Erreur lors de l'ajout de l'observable {1} de type {0} - {2} ({3})".format(
                            observable_header["type"],
                            observable_header["value"],
                            response.status_code,
                            response.text,
                        ),
                    }
                    sio.emit("status", json.dumps(message))

        # Add observables found in the mail body
        for observable_body in observables_body:
            observable = thehive4py.models.CaseObservable(
                dataType=observable_body["type"],
                data=observable_body["value"],
                ioc=False,
                tags=["email", "email_body"],
                message="Found in the email body",
            )
            response = api_thehive.create_case_observable(new_id, observable)
            if response.status_code == 201:
                log.info(
                    "Added observable {0}: {1} to case {2}".format(
                        observable_body["type"], observable_body["value"], new_case_id
                    )
                )
                message = {
                    "event": "satus",
                    "data": "Observable {1} de type {0} ajouté au cas {2}".format(
                        observable_header["type"],
                        observable_header["value"],
                        new_case_id,
                    ),
                }
                sio.emit("status", json.dumps(message))
            else:
                log.debug(
                    "Cannot add observable {0}: {1} - {2} ({3})".format(
                        observable_body["type"],
                        observable_body["value"],
                        response.status_code,
                        response.text,
                    )
                )
                message = {
                    "event": "satus",
                    "data": "Erreur lors de l'ajout de l'observable {1} de type {0} - {2} ({3})".format(
                        observable_header["type"],
                        observable_header["value"],
                        response.status_code,
                        response.text,
                    ),
                }
                sio.emit("status", json.dumps(message))

        # Add attachments
        for attachment in attachments:
            observable = thehive4py.models.CaseObservable(
                dataType="file",
                data=attachment,
                ioc=False,
                tags=["email", "email_attachment"],
                message="Found as email attachment",
            )
            response = api_thehive.create_case_observable(new_id, observable)
            if response.status_code == 201:
                log.info(
                    "Added observable file {0} to case {1}".format(
                        attachment[1], new_case_id
                    )
                )
                message = {
                    "event": "satus",
                    "data": "Pièce jointe {0} ajoutée au cas {1}".format(
                        attachment[1], new_case_id
                    ),
                }
                sio.emit("status", json.dumps(message))
            else:
                log.debug(
                    "Cannot add observable: file {0} - {1} ({2})".format(
                        attachment[1], response.status_code, response.text
                    )
                )
                message = {
                    "event": "satus",
                    "data": "Erreur lors de l'ajout de la pièce jointe {0} - {1} ({2})".format(
                        attachment[1], response.status_code, response.text
                    ),
                }
                sio.emit("status", json.dumps(message))

        # Add hashes of the attachments
        for hash_attachment in hashes_attachments:
            observable = thehive4py.models.CaseObservable(
                dataType="hash",
                data=hash_attachment["hashValue"],
                ioc=False,
                tags=["email", "email_attachment_hash"],
                message='Hash of attachment "{}"'.format(
                    hash_attachment["hashedAttachment"]
                ),
            )
            response = api_thehive.create_case_observable(new_id, observable)
            if response.status_code == 201:
                log.info(
                    "Added observable hash: {0} to case {1}".format(
                        hash_attachment["hashValue"], new_case_id
                    )
                )
                message = {
                    "event": "satus",
                    "data": "Hash {0} ajouté au cas {1}".format(
                        hash_attachment["hashValue"], new_case_id
                    ),
                }
                sio.emit("status", json.dumps(message))
            else:
                log.debug(
                    "Cannot add observable hash: {0} - {1} ({2})".format(
                        hash_attachment["hashValue"],
                        response.status_code,
                        response.text,
                    )
                )
                message = {
                    "event": "satus",
                    "data": "Erreur lors de l'ajout du hash {0} - {1} ({2})".format(
                        hash_attachment["hashValue"],
                        response.status_code,
                        response.text,
                    ),
                }
                sio.emit("status", json.dumps(message))

        # Add eml file (using the tuple)
        if eml_file_tuple:
            observable = thehive4py.models.CaseObservable(
                dataType="file",
                data=eml_file_tuple,
                ioc=False,
                tags=["email", "email_sample"],
                message="Attached email in eml format",
            )
            response = api_thehive.create_case_observable(new_id, observable)
            if response.status_code == 201:
                log.info(
                    "Added observable file {0} to case {1}".format(
                        eml_file_tuple[1], new_case_id
                    )
                )
                message = {
                    "event": "satus",
                    "data": "Pièce jointe {0} ajoutée au cas {1}".format(
                        eml_file_tuple[1], new_case_id
                    ),
                }
                sio.emit("status", json.dumps(message))
            else:
                log.debug(
                    "Cannot add observable: file {0} - {1} ({2})".format(
                        eml_file_tuple[1], response.status_code, response.text
                    )
                )
                message = {
                    "event": "satus",
                    "data": "Erreur lors de l'ajout de la pièce jointe {0} - {1} ({2})".format(
                        eml_file_tuple[1], response.status_code, response.text
                    ),
                }
                sio.emit("status", json.dumps(message))

    else:
        log.error(
            "Cannot create case: {0} ({1})".format(response.status_code, response.text)
        )
        message = {
            "event": "satus",
            "data": "Erreur lors de la création du cas: {0} ({1})".format(
                response.status_code, response.text
            ),
        }
        sio.emit("status", json.dumps(message))
        return

    log.info("Created case : {0}".format(new_case_id))
    message = {
        "event": "satus",
        "data": "Cas The Hive créé: {0}".format(new_case_id),
    }
    sio.emit("status", json.dumps(message))
    # Return the id of the just created case on which to run the analysis
    return new_case


# Send the notification to the user
def notify_start_of_analysis(case, task_id, mail_to, sio):
    # Add a description to the first task that is understood by the Mailer responder and start it
    # The description must start with "mailto:<email>" and then continue with the body of the email to send to the user
    # Uses [11:] to filter out the prefix [PhishAndChips] in the name of the case
    task_notification = thehive4py.models.CaseTask(
        id=task_id,
        description="mailto:"
        + mail_to
        + "\nThanks for the submission. Your e-mail with subject [{0}] is being analyzed.".format(
            case.json()["title"][11:]
        ),
        status="InProgress",
    )
    api_thehive.update_case_task(task_notification, fields=["description", "status"])

    message = {
        "event": "satus",
        "data": "Début de l'analyse Cortex",
    }
    sio.emit("status", json.dumps(message))

    # Obtain the representation of the Mailer responder
    mailer_responder = api_cortex.responders.get_by_name("Mailer_1_0")
    # Check if the responder has been enabled in Cortex
    if mailer_responder:
        # Obtain the ID of the Mailer responder and start the Mailer responder on the first task
        job_mailer_id = api_thehive.run_responder(
            mailer_responder.id, "case_task", task_id
        ).json()["cortexJobId"]
        # Obtain the status of the job related to the Mailer responder and wait for its completion
        job_mailer_status = api_cortex.jobs.get_by_id(job_mailer_id).json()["status"]
        while job_mailer_status not in ["Success", "Failure"]:
            time.sleep(2)
            job_mailer_status = api_cortex.jobs.get_by_id(job_mailer_id).json()[
                "status"
            ]
        if job_mailer_status == "Success":
            log.info("Notification mail sent")
        else:
            log.warning("Something went wrong with the Mailer responder")
    else:
        log.warning("The Mailer responder is not active")
    # Close the task
    task_notification = thehive4py.models.CaseTask(id=task_id, status="Completed")
    api_thehive.update_case_task(task_notification, fields=["status"])


# Start the analyzers on the observables
def analyze_observables(case, task_id, sio):
    # Start the second task
    task_analysis = thehive4py.models.CaseTask(id=task_id, status="InProgress")
    api_thehive.update_case_task(task_analysis, fields=["status"])

    # Obtain the observable list from the case
    observables_json = api_thehive.get_case_observables(case.json()["id"]).json()

    # Create a list of jobs with:
    # - job_id
    # - id of the observable to which the job refers
    # - job status
    jobs = []

    # Create a list of delayed jobs with:
    # - analyzer name
    # - observable name on which to start the analyzer
    # - observable type on which to start the analyzer
    # - id of the observable on which to start the analyzer
    delayed_jobs = []

    # List that will contain the reports of each analyzer for each observable
    reports_observables = []

    # Create a list containing information about all the observables of the case with:
    # - Name
    # - Type
    # - Tags list
    # - alphanumeric ID
    observables_info = []

    # Dictionary that contains the list of enabled and applicable analyzers for each observable type
    applicable_analyzers = {}
    applicable_analyzers["file"] = api_cortex.analyzers.get_by_type("file")
    applicable_analyzers["url"] = api_cortex.analyzers.get_by_type("url")
    applicable_analyzers["domain"] = api_cortex.analyzers.get_by_type("domain")
    applicable_analyzers["ip"] = api_cortex.analyzers.get_by_type("ip")
    applicable_analyzers["mail"] = api_cortex.analyzers.get_by_type("mail")
    applicable_analyzers["hash"] = api_cortex.analyzers.get_by_type("hash")

    # For each observable, add its information to the dictionary
    for observable in observables_json:
        observable_info = {}
        # The needed information are in different places depending on the type of the observable
        if observable["dataType"] == "file":
            observable_info["name"] = observable["attachment"]["name"]
            if (observable["attachment"]["contentType"] == "message/rfc822") or (
                observable["attachment"]["contentType"]
                in ["application/x-empty", "text/plain"]
                and observable_info["name"][-4:] == ".eml"
            ):
                observable_info["type"] = (
                    observable["dataType"] + "_" + "message/rfc822"
                )
            else:
                observable_info["type"] = observable["dataType"]
        else:
            observable_info["name"] = observable["data"]
            observable_info["type"] = observable["dataType"]
        observable_info["tags"] = observable["tags"]
        observable_info["id"] = observable["id"]
        observables_info.append(observable_info)

        # If it is the EML file, then create a new observable type and only execute yara
        if observable_info["type"] == "file_message/rfc822":
            # Start the job related to the Yara analyzer if it is enabled
            for analyzer in applicable_analyzers["file"]:
                if analyzer.name == "Yara_2_0":
                    # Create the job object
                    job = {}
                    # Run the analyzer and convert the response in JSON format, then obtain and save the job ID
                    job["job_id"] = api_thehive.run_analyzer(
                        config["cortexID"], observable_info["id"], analyzer.name
                    ).json()["cortexJobId"]
                    # Save the observable ID
                    job["observable_id"] = observable_info["id"]
                    # Set the status to NotTerminated
                    job["status"] = "NotTerminated"
                    # Add the job with all the needed information to the list
                    jobs.append(job)
                    log.info(
                        "Started analyzer "
                        + analyzer.name
                        + " for "
                        + observable_info["type"]
                        + " "
                        + observable_info["name"]
                    )
                    message = {
                        "event": "satus",
                        "data": "Analyse de l'observable {0} {1} avec l'analyzer {2}".format(
                            observable_info["type"],
                            observable_info["name"],
                            analyzer.name,
                        ),
                    }
                    sio.emit("status", json.dumps(message))

        # Otherwise, if it is a URL, start the UnshortenLink analyzer
        if observable_info["type"] == "url":
            for analyzer in applicable_analyzers[observable_info["type"]]:
                if analyzer.name == "UnshortenLink_1_2":
                    # Start the UnshortenLink analyzer
                    job_ul_id = api_thehive.run_analyzer(
                        config["cortexID"], observable_info["id"], "UnshortenLink_1_2"
                    ).json()["cortexJobId"]
                    log.info(
                        "Started analyzer "
                        + analyzer.name
                        + " for "
                        + observable_info["type"]
                        + " "
                        + observable_info["name"]
                    )
                    message = {
                        "event": "satus",
                        "data": "Analyse de l'observable {0} {1} avec l'analyzer {2}".format(
                            observable_info["type"],
                            observable_info["name"],
                            analyzer.name,
                        ),
                    }
                    sio.emit("status", json.dumps(message))
                    # Obtain the status of the job related to the UnshortenLink analyzer and wait for its completion
                    job_ul_status = api_cortex.jobs.get_by_id(job_ul_id).json()[
                        "status"
                    ]
                    while job_ul_status not in ["Success", "Failure"]:
                        time.sleep(2)
                        job_ul_status = api_cortex.jobs.get_by_id(job_ul_id).json()[
                            "status"
                        ]
                    unshortened_url = ""
                    # If a shortened link has been found, save it
                    if job_ul_status == "Success":
                        job_ul = api_cortex.jobs.get_report(job_ul_id).json()
                        if job_ul["report"]["full"]["found"] == True:
                            unshortened_url = job_ul["report"]["full"]["url"]
                    # Add the unshortened link as an observable to the case
                    if len(unshortened_url) > 0:
                        new_observable = thehive4py.models.CaseObservable(
                            dataType="url",
                            data=[unshortened_url],
                            ioc=False,
                            tags=["unshortened_url"],
                            message="Unshortened from {}".format(
                                observable_info["name"]
                            ),
                        )
                        response = api_thehive.create_case_observable(
                            case.json()["id"], new_observable
                        )
                        log.info(
                            "Added unshortened url: {} as observable".format(
                                unshortened_url
                            )
                        )
                        # Add the just created observable also to the list of observables on which the cycle is running, so that it will be analyzed as well
                        if response.status_code == 201:
                            new_obs = api_thehive.get_case_observable(
                                response.json()[0]["id"]
                            ).json()
                            observables_json.append(new_obs)
                            obs_unshortened_info = {}
                            obs_unshortened_info["name"] = new_obs["data"]
                            obs_unshortened_info["type"] = new_obs["dataType"]
                            obs_unshortened_info["tags"] = new_obs["tags"]
                            obs_unshortened_info["id"] = new_obs["id"]
                            observables_info.append(obs_unshortened_info)
                            log.info(
                                "Analyzer "
                                + analyzer.name
                                + " for "
                                + observable_info["type"]
                                + " "
                                + observable_info["name"]
                                + " terminated. Added the url "
                                + unshortened_url
                                + " as new observable to the case."
                            )

        # Start all the applicable analyzers if the observable is not the EML file
        if observable_info["type"] != "file_message/rfc822":
            for analyzer in applicable_analyzers[observable_info["type"]]:
                # The DomainMailSPFDMARC_Analyzer should only be started on domains that should be able to send emails
                # It is started only on observables found in a subset of the header fields
                # which are the observables tagged as contained in the email header and, in particular, in one of the considered header fields
                # The third tag of the observable should be email_header_HEADERNAME, so the prefix email_header_ is removed
                header_fields_list_SPFDMARC = [
                    "From",
                    "Sender",
                    "Return-Path",
                    "Reply-To",
                    "Bounces-to",
                    "Received",
                    "X-Received",
                    "X-OriginatorOrg",
                    "X-Originating-Email",
                ]
                if analyzer.name == "DomainMailSPFDMARC_Analyzer_1_1" and not (
                    observable_info["type"] == "domain"
                    and observable_info["tags"][1] == "email_header"
                    and observable_info["tags"][2][13:] in header_fields_list_SPFDMARC
                ):
                    continue
                # If it is an URL, do not start UnshortenLink again
                if (
                    observable_info["type"] == "url"
                    and analyzer.name == "UnshortenLink_1_2"
                ):
                    continue
                # Start the analyzer
                analyzer_job = api_thehive.run_analyzer(
                    config["cortexID"], observable_info["id"], analyzer.name
                )
                # If the rate limit is exceeded for a certain analyzer, the related job is not started
                # so the information needed to start the job later is added to a list of delayed jobs
                if "RateLimitExceeded" in str(analyzer_job.json()):
                    log.info(
                        "Rate limit exceeded for analyzer "
                        + analyzer.name
                        + " for "
                        + observable_info["type"]
                        + " "
                        + observable_info["name"]
                        + ". It will be restarted in a while."
                    )
                    delayed_job = {}
                    delayed_job["analyzer_name"] = analyzer.name
                    delayed_job["observable_name"] = observable_info["name"]
                    delayed_job["observable_type"] = observable_info["type"]
                    delayed_job["observable_id"] = observable_info["id"]
                    delayed_jobs.append(delayed_job)
                # else add the information of the job to the list of started jobs
                else:
                    job = {}
                    message = {
                        "event": "satus",
                        "data": "analyzer_job {0}".format(analyzer_job.json()),
                    }
                    sio.emit("status", json.dumps(message))
                    job["job_id"] = analyzer_job.json()["cortexJobId"]
                    job["observable_id"] = observable_info["id"]
                    job["status"] = "NotTerminated"
                    jobs.append(job)
                    log.info(
                        "Started analyzer "
                        + analyzer.name
                        + " for "
                        + observable_info["type"]
                        + " "
                        + observable_info["name"]
                    )
                    message = {
                        "event": "satus",
                        "data": "Analyse de l'observable {0} {1} avec l'analyzer {2}".format(
                            observable_info["type"],
                            observable_info["name"],
                            analyzer.name,
                        ),
                    }
                    sio.emit("status", json.dumps(message))

    # Try to start the delayed analyzers until the list of delayed analyzers becomes empty
    while len(delayed_jobs) > 0:
        for delayed_job in delayed_jobs:
            # Try to start the analyzer
            analyzer_job = api_thehive.run_analyzer(
                config["cortexID"],
                delayed_job["observable_id"],
                delayed_job["analyzer_name"],
            )
            # If the rate limit is still exceeded for this analyzer, do not remove it from the list of delayed jobs
            if "RateLimitExceeded" in str(analyzer_job.json()):
                log.info(
                    "Rate limit exceeded for analyzer "
                    + delayed_job["analyzer_name"]
                    + " for "
                    + delayed_job["observable_type"]
                    + " "
                    + delayed_job["observable_name"]
                    + ". It will be restarted in a while."
                )
            # Otherwise start the analyzer, add it to the list of started analyzers and remove it from the list of delayed analyzers
            else:
                job = {}
                job["job_id"] = analyzer_job.json()["cortexJobId"]
                job["observable_id"] = delayed_job["observable_id"]
                job["status"] = "NotTerminated"
                jobs.append(job)
                delayed_jobs.remove(delayed_job)
                log.info(
                    "Started analyzer "
                    + delayed_job["analyzer_name"]
                    + " for "
                    + delayed_job["observable_type"]
                    + " "
                    + delayed_job["observable_name"]
                )
                message = {
                    "event": "satus",
                    "data": "Analyse de l'observable {0} {1} avec l'analyzer {2}".format(
                        observable_info["type"],
                        observable_info["name"],
                        analyzer.name,
                    ),
                }
                sio.emit("status", json.dumps(message))
        # Prevent continuous requests while waiting for the time needed to start an analyzer
        time.sleep(10)

    log.info("All the analysis jobs have been started, waiting for their completion...")
    message = {
        "event": "satus",
        "data": "En attente du résultat de l'analyse...",
    }
    sio.emit("status", json.dumps(message))

    # Wait for all the jobs to terminate
    terminated_jobs = 0
    # Wait until the number of terminated jobs is equal to the number of started jobs
    while terminated_jobs != len(jobs):
        # Prevent continuous requests while waiting for all the analyzers to terminate
        time.sleep(5)
        for job_obj in jobs:
            # Request the status of the job and if it is terminated increment the number of terminated jobs
            if job_obj["status"] == "NotTerminated":
                job = api_cortex.jobs.get_by_id(job_obj["job_id"]).json()
                if job["status"] == "Success" or job["status"] == "Failure":
                    job_obj["status"] = job["status"]
                    terminated_jobs += 1

    log.info("All the analysis jobs terminated")
    message = {
        "event": "satus",
        "data": "Tâches d'analyse terminées",
    }
    sio.emit("status", json.dumps(message))

    # For each observable, find the ID of all the analyzers started on that observable and use it to fetch the report of that analyzer (job)
    for observable_info in observables_info:
        for job_obj in jobs:
            if observable_info["id"] == job_obj["observable_id"]:
                # Obtain the report
                job = api_cortex.jobs.get_report(job_obj["job_id"]).json()
                # Add the report along with all the needed information on the observable and the analyzer to the list of reports
                report_obs = {}
                report_obs["observable_name"] = observable_info["name"]
                report_obs["observable_type"] = observable_info["type"]
                report_obs["observable_id"] = observable_info["id"]
                report_obs["analyzer_name"] = job["analyzerName"]
                # The report is populated only if the job terminated successfully
                report_obs["analyzer_result"] = ""
                if job["status"] == "Success":
                    # Handle the possibility that a job terminates successfully but the report does not contain the level
                    # In that case the level defaults as "info"
                    level = "info"
                    report = job.get("report")
                    if report:
                        summary = report.get("summary")
                        if summary:
                            taxonomies = summary.get("taxonomies")
                            if taxonomies and len(taxonomies) > 0:
                                # Handle Pulsedive
                                # Many taxonomies are created, only the last one is needed
                                if job["analyzerName"] == "Pulsedive_GetIndicator_1_0":
                                    level = taxonomies[-1].get("level", "info")
                                # Handle IPVoid
                                # Many taxonomies are created, only the last one is needed
                                elif job["analyzerName"] == "IPVoid_1_0":
                                    level = taxonomies[-1].get("level", "info")
                                # Handle Shodan
                                # Many taxonomies are created, only the last one is needed
                                # The other analyzers based on shodan only give "info" as level
                                elif job["analyzerName"] in [
                                    "Shodan_Host_1_0",
                                    "Shodan_Host_History_1_0",
                                ]:
                                    level = taxonomies[-1].get("level", "info")
                                # Handle SpamhausDBL
                                # The first taxonomy contains the return code that if it is among the codes listed below it means that the level should be malicious
                                elif job["analyzerName"] == "SpamhausDBL_1_0":
                                    if taxonomies[0].get("value", "NXDOMAIN") in [
                                        "127.0.1.2",
                                        "127.0.1.4",
                                        "127.0.1.5",
                                        "127.0.1.6",
                                        "127.0.1.102",
                                        "127.0.1.103",
                                        "127.0.1.104",
                                        "127.0.1.105",
                                        "127.0.1.106",
                                    ]:
                                        level = "malicious"
                                # For all the other analyzers uses the first taxonomy
                                else:
                                    level = taxonomies[0].get("level", "info")

                    # Handle URLhaus
                    # md5_hash and sha256_hash are supported only for payload search and not also for URL or hosts (IP, domains)
                    # Without this modification it is always given a level of "info" even though it should be "malicious"
                    # So, if "info" is obtained, check in the full report if there is a threat and, if so, set the level to "malicious"
                    if (
                        job["analyzerName"] == "URLhaus_2_0"
                        and job["report"]["full"]["query_status"] == "ok"
                        and job["report"]["full"].get("threat")
                    ):
                        level = "malicious"

                    # Handle analyzers levels
                    # Often happens that the level given by an analyzer is too high for some or all the observable types on which it is applicable, leading to false positives
                    # It is then used a configuration file which is a dictionary containing, for each analyzer that has to be modified:
                    # - dataType: types of the observables on which to apply the modification
                    # - level mapping
                    if job["analyzerName"] in conf_analyzers_level:
                        if (
                            observable_info["type"]
                            in conf_analyzers_level[job["analyzerName"]]["dataType"]
                        ):
                            level = conf_analyzers_level[job["analyzerName"]][
                                "levelMapping"
                            ][level]

                    # Save the level in the report
                    report_obs["analyzer_result"] = level
                    log.info(
                        "Analyzer {0} terminated successfully for {1} {2} with verdict {3}".format(
                            job["analyzerName"],
                            report_obs["observable_type"],
                            report_obs["observable_name"],
                            report_obs["analyzer_result"],
                        )
                    )
                    message = {
                        "event": "satus",
                        "data": "Résultat de l'analyzer {0} pour {1} {2} : {3}".format(
                            job["analyzerName"],
                            report_obs["observable_type"],
                            report_obs["observable_name"],
                            report_obs["analyzer_result"],
                        ),
                    }
                    sio.emit("status", json.dumps(message))
                else:
                    log.warning(
                        "Something went wrong with analyzer {0} for {1} {2}: {3}".format(
                            job["analyzerName"],
                            report_obs["observable_type"],
                            report_obs["observable_name"],
                            job,
                        )
                    )
                    message = {
                        "event": "satus",
                        "data": "Erreur de l'analyzer {0} pour {1} {2} : {3}".format(
                            job["analyzerName"],
                            report_obs["observable_type"],
                            report_obs["observable_name"],
                            job,
                        ),
                    }
                    sio.emit("status", json.dumps(message))

                # Add the report to the list of reports
                reports_observables.append(report_obs)

    # Close the second task
    task_analysis = thehive4py.models.CaseTask(id=task_id, status="Completed")
    api_thehive.update_case_task(task_analysis, fields=["status"])

    return observables_info, reports_observables


def terminate_analysis(
    case, task_id, mail_to, observables_info, reports_observables, sio
):
    message = {
        "event": "satus",
        "data": "Envoi du mail de résultat",
    }
    sio.emit("status", json.dumps(message))
    # Start the third task
    task_result = thehive4py.models.CaseTask(id=task_id, status="InProgress")
    api_thehive.update_case_task(task_result, fields=["status"])

    # Initialize the number of malicious and suspicious observables to 0
    malicious_observables = 0
    suspicious_observables = 0

    # Count the number of malicious and suspicious reports for each observable
    for observable_info in observables_info:
        malicious_reports = 0
        suspicious_reports = 0
        for report_obs in reports_observables:
            if report_obs["observable_id"] == observable_info["id"]:
                if report_obs["analyzer_result"] == "malicious":
                    malicious_reports += 1
                elif report_obs["analyzer_result"] == "suspicious":
                    suspicious_reports += 1
        # If the number of malicious reports is > 0 for this observable, the observable is malicious
        if malicious_reports > 0:
            malicious_observables += 1
            # Mark the observable as IoC
            obs_to_update = thehive4py.models.CaseObservable(
                id=observable_info["id"], ioc=True
            )
            api_thehive.update_case_observables(obs_to_update, fields=["ioc"])
        # If the number of suspicious reports is > 0 for this observable, the observable is suspicious
        if suspicious_reports > 0:
            suspicious_observables += 1

    # If there is at least one malicious observable, then the email is malicious
    if malicious_observables > 0:
        verdict = "Malicious"
    # If there is at least one suspicious observable, then the email is suspicious
    elif suspicious_observables > 0:
        verdict = "Suspicious"
    # Else the email is safe
    else:
        verdict = "Safe"
    log.info("The email has been classified as " + verdict)

    # If the verdict is final close the task and the case
    if verdict == "Malicious" or verdict == "Suspicious":
        # If the verdict is malicious or suspicious, export also the case to MISP along with the observables marked as IoC
        export_result = api_thehive.export_to_misp(config["mispID"], case.json()["id"])
        if export_result.ok:
            log.info("Case exported to MISP")
        else:
            log.warning("An error occurred during the export to MISP")
        resolution_status = "TruePositive"
        impact_status = "NoImpact"

    elif verdict == "Safe":
        resolution_status = "FalsePositive"
        impact_status = "NotApplicable"

    # Add a description to the third task that is understood by the Mailer responder
    # The description must start with "mailto:<email>" and then continue with the body of the email to send to the user
    task_result = thehive4py.models.CaseTask(
        id=task_id,
        description="mailto:"
        + mail_to
        + "\nThanks for your submission. The e-mail with subject [{0}] you submitted has been classified as {1}".format(
            case.json()["title"][11:], verdict
        ),
    )
    api_thehive.update_case_task(task_result, fields=["description"])
    # Obtain the representation of the Mailer responder
    mailer_responder = api_cortex.responders.get_by_name("Mailer_1_0")
    # Check if the responder has been enabled in Cortex
    if mailer_responder:
        # Obtain the ID of the Mailer responder and start the Mailer responder on the third task
        job_mailer_id = api_thehive.run_responder(
            mailer_responder.id, "case_task", task_id
        ).json()["cortexJobId"]
        # Obtain the status of the job related to the Mailer responder and wait for its completion
        job_mailer_status = api_cortex.jobs.get_by_id(job_mailer_id).json()["status"]
        while job_mailer_status not in ["Success", "Failure"]:
            time.sleep(2)
            job_mailer_status = api_cortex.jobs.get_by_id(job_mailer_id).json()[
                "status"
            ]
        if job_mailer_status == "Success":
            log.info("Response mail sent")
        else:
            log.warning("Something went wrong with the Mailer responder")
    else:
        log.warning("The Mailer responder is not active")
    # Close the task
    task_result = thehive4py.models.CaseTask(id=task_id, status="Completed")
    api_thehive.update_case_task(task_result, fields=["status"])

    # Close the case
    thehive4py.models.CaseHelper(api_thehive).update(
        case.json()["id"],
        status="Resolved",
        resolutionStatus=resolution_status,
        impactStatus=impact_status,
        summary="Automated analysis",
    )
    log.info("Case resolved as " + resolution_status)
    message = {
        "event": "satus",
        "data": "Case resolved as {}".format(resolution_status),
    }
    sio.emit("status", json.dumps(message))

    return verdict


# function to run the analysis of the case
# The mail_to parameter is the email address of the user to send notifications to
def run_analysis(case, mail_to, sio):
    global config
    global log
    global api_thehive
    global api_cortex
    global conf_analyzers_level

    # TheHive, Cortex and MISP configuration
    try:
        with open(conf_file_path) as conf_file:
            conf_dict = json.load(conf_file)
            config["cortexURL"] = conf_dict["cortex"]["url"]
            config["cortexApiKey"] = conf_dict["cortex"]["apikey"]
            config["cortexID"] = conf_dict["cortex"]["id"]
            config["mispID"] = conf_dict["misp"]["id"]
    except Exception as e:
        log.error(
            "Error while trying to open the file 'configuration.json': {}".format(
                traceback.format_exc()
            )
        )
        message = {
            "event": "satus",
            "data": "Erreur lors de l'ouverture du fichier 'configuration.json' {}".format(
                traceback.format_exc()
            ),
        }
        sio.emit("status", json.dumps(message))
        return

    # Read the configuration file for the analyzers levels modification
    try:
        with open(analyzers_conf_file_path) as conf_file:
            conf_analyzers_level = json.load(conf_file)
    except Exception as e:
        log.error(
            "Error while trying to open the file 'analyzers_level_conf.json': {}".format(
                traceback.format_exc()
            )
        )
        message = {
            "event": "satus",
            "data": "Erreur lors de l'ouverture du fichier 'analyzers_level_conf.json.json' {}".format(
                traceback.format_exc()
            ),
        }
        sio.emit("status", json.dumps(message))
        return

    # Objects needed to use Cortex4py
    api_cortex = cortex4py.api.Api(config["cortexURL"], config["cortexApiKey"])

    # Obtain the IDS of the three tasks of the case
    tasks = api_thehive.get_case_tasks(case.json()["id"]).json()
    log.info("case")
    log.info(case.json())
    log.info("tasks")
    log.info(tasks)
    task_ids = {}
    for task in tasks:
        if task["title"] == "PhishAndChips notification":
            task_ids["Notification"] = task["id"]
        elif task["title"] == "PhishAndChips analysis":
            task_ids["Analysis"] = task["id"]
        elif task["title"] == "PhishAndChips result":
            task_ids["Result"] = task["id"]

    # Call the notify_start_of_analysis function
    try:
        notify_start_of_analysis(case, task_ids["Notification"], mail_to, sio)
    except Exception as e:
        log.error(
            "Error while trying to notify the start of analysis: {}".format(
                traceback.format_exc()
            )
        )
        message = {
            "event": "satus",
            "data": "Erreur lors de l'envoi de la notification du début d'analyse: {}".format(
                traceback.format_exc()
            ),
        }
        sio.emit("status", json.dumps(message))
        return

    # Call the analyze_observables function
    try:
        observables_info, reports_observables = analyze_observables(
            case, task_ids["Analysis"], sio
        )
    except Exception as e:
        log.error("Error during the analysis task: {}".format(traceback.format_exc()))
        message = {
            "event": "satus",
            "data": "Erreur lors de l'analyse: {}".format(traceback.format_exc()),
        }
        sio.emit("status", json.dumps(message))
        return

    log.info("Analyse complète")
    message = {"event": "satus", "data": "Analyse complète"}
    sio.emit("status", json.dumps(message))
    # Call the terminate_analysis function
    try:
        verdict = terminate_analysis(
            case,
            task_ids["Result"],
            mail_to,
            observables_info,
            reports_observables,
            sio,
        )
    except Exception as e:
        log.error(
            "Error during the termination of the analysis: {}".format(
                traceback.format_exc()
            )
        )
        message = {
            "event": "satus",
            "data": "Erreur lors de la fin de l'analyse: {}".format(
                traceback.format_exc()
            ),
        }
        sio.emit("status", json.dumps(message))
        return

    message = {
        "event": "satus",
        "data": "Résultat de l'analyse: {}".format(verdict),
    }
    sio.emit("status", json.dumps(message))
    return verdict


# Main function called from outside
def main(mail_uid, port):
    global config
    global log
    global api_thehive
    global api_cortex
    global whitelist

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

    # Web Socket to send messages to Nest server
    # The ws is not a global variable to support multiple tab
    # Créer une instance SocketIO
    sio = socketio.Client()

    @sio.event
    def connect():
        global log
        log.info("Connected to Socket.IO server")

    @sio.event
    def disconnect():
        global log
        log.info("Disconnected from Socket.IO server")

    sio.connect(
        f"http://localhost:{port}", headers={"Access-Control-Allow-Origin": "*"}
    )

    message = {"event": "satus", "data": "Début de l'analyse"}
    sio.emit("status", json.dumps(message))
    try:
        with open(conf_file_path) as conf_file:
            conf_dict = json.load(conf_file)

            # TheHive configuration
            config["thehiveURL"] = conf_dict["thehive"]["url"]
            config["thehiveApiKey"] = conf_dict["thehive"]["apikey"]

            # New case configuration
            config["caseTLP"] = conf_dict["case"]["tlp"]
            config["casePAP"] = conf_dict["case"]["pap"]
            config["caseTags"] = conf_dict["case"]["tags"]

    except Exception as e:
        log.error(
            "Error while trying to open the file 'configuration.json': {}".format(
                traceback.format_exc()
            )
        )
        message = {
            "event": "satus",
            "data": "Erreur lors de l'ouverture de 'configuration.json': {}".format(
                traceback.format_exc()
            ),
        }
        sio.emit("status", json.dumps(message))
        time.sleep(1)  # Attendre 1 seconde pour s'assurer que le message est envoyé
        sio.disconnect()
        return

    # Read the whitelist file, which is composed by various parts:
    # - The exact matching part
    # - The regex matching part
    # - Three lists of domains that are used to whitelist subdomains, URLs and email addresses that contain them
    try:
        message = {"event": "satus", "data": "Vérification de la whitelist"}
        sio.emit("status", json.dumps(message))
        with open(whitelist_file_path) as whitelist_file:
            whitelist_dict = json.load(whitelist_file)
            whitelist["mailExact"] = whitelist_dict["exactMatching"]["mail"]
            whitelist["mailRegex"] = whitelist_dict["regexMatching"]["mail"]
            whitelist["ipExact"] = whitelist_dict["exactMatching"]["ip"]
            whitelist["ipRegex"] = whitelist_dict["regexMatching"]["ip"]
            whitelist["domainExact"] = whitelist_dict["exactMatching"]["domain"]
            whitelist["domainRegex"] = whitelist_dict["regexMatching"]["domain"]
            whitelist["urlExact"] = whitelist_dict["exactMatching"]["url"]
            whitelist["urlRegex"] = whitelist_dict["regexMatching"]["url"]
            whitelist["filenameExact"] = whitelist_dict["exactMatching"]["filename"]
            whitelist["filenameRegex"] = whitelist_dict["regexMatching"]["filename"]
            whitelist["filetypeExact"] = whitelist_dict["exactMatching"]["filetype"]
            whitelist["hashExact"] = whitelist_dict["exactMatching"]["hash"]

            # The domains in the last three lists are used to create three lists of regular expressions that serve to whitelist subdomains, URLs and email addresses based on those domains
            whitelist["regexDomainsInSubdomains"] = [
                r"^(.+\.|){0}$".format(domain.replace(r".", r"\."))
                for domain in whitelist_dict["domainsInSubdomains"]
            ]
            whitelist["regexDomainsInURLs"] = [
                r"^(http|https):\/\/([^\/]+\.|){0}(\/.*|\?.*|\#.*|)$".format(
                    domain.replace(r".", r"\.")
                )
                for domain in whitelist_dict["domainsInURLs"]
            ]
            whitelist["regexDomainsInEmails"] = [
                r"^.+@(.+\.|){0}$".format(domain.replace(r".", r"\."))
                for domain in whitelist_dict["domainsInEmails"]
            ]

    except Exception as e:
        log.error(
            "Error while trying to open the file 'whitelist.json': {}".format(
                traceback.format_exc()
            )
        )
        message = {
            "event": "satus",
            "data": "Erreur lors de l'ouverture de 'whitelist.json': {}".format(
                traceback.format_exc()
            ),
        }
        sio.emit("status", json.dumps(message))
        time.sleep(1)  # Attendre 1 seconde pour s'assurer que le message est envoyé
        sio.disconnect()
        return

    # Object needed to use TheHive4py
    api_thehive = thehive4py.api.TheHiveApi(
        config["thehiveURL"], config["thehiveApiKey"]
    )
    message = {"event": "satus", "data": "Connexion à The Hive"}
    sio.emit("status", json.dumps(message))
    try:
        # Vérifier la connexion en obtenant les alertes existantes
        response = api_thehive.health()

        # Vérifier si la requête a réussi (code de statut 200)
        if response.status_code == 200:
            log.info("Connexion établie avec succès !")
            message = {"event": "satus", "data": "Connexion à The Hive établie"}
            sio.emit("status", json.dumps(message))
        else:
            log.error(
                "Erreur lors de la récupération des alertes. Code de statut : {}".format(
                    response.status_code
                )
            )
            message = {
                "event": "satus",
                "data": "Erreur lors de la récupération des alertes. Code de statut : {}".format(
                    response.status_code
                ),
            }
            sio.emit("status", json.dumps(message))
            time.sleep(1)  # Attendre 1 seconde pour s'assurer que le message est envoyé
            sio.disconnect()
            return
    except Exception as e:
        log.error("Erreur lors de la connexion à l'API : {}".format(str(e)))
        message = {
            "event": "satus",
            "data": "Erreur lors de la connexion à l'API : {}".format(str(e)),
        }
        sio.emit("status", json.dumps(message))
        time.sleep(1)  # Attendre 1 seconde pour s'assurer que le message est envoyé
        sio.disconnect()
        return

    # Connect to Gmail API
    try:
        message = {"event": "satus", "data": "Connexion à l'API Gmail"}
        sio.emit("status", json.dumps(message))
        connection = connect_to_Gmail_API(sio)
    except Exception as e:
        log.error(
            "Error while trying to connect to Gmail API: {}".format(
                traceback.format_exc()
            )
        )
        message = {
            "event": "satus",
            "data": "Erreur lors de la connexion à l'API : {}".format(
                traceback.format_exc()
            ),
        }
        sio.emit("status", json.dumps(message))
        time.sleep(1)  # Attendre 1 seconde pour s'assurer que le message est envoyé
        sio.disconnect()
        return

    # Call the obtain_eml function
    try:
        message = {"event": "satus", "data": "Récupération de la pièce jointe eml"}
        sio.emit("status", json.dumps(message))
        internal_msg, external_from_field = obtain_eml(connection, mail_uid, sio)
        log.info("externals :")
        log.info(external_from_field)
    except Exception as e:
        log.error(
            "Error while trying to obtain the internal eml file: {}".format(
                traceback.format_exc()
            )
        )
        message = {
            "event": "satus",
            "data": "Erreur lors de l'obtention de la pièce jointe eml: {}".format(
                traceback.format_exc()
            ),
        }
        sio.emit("status", json.dumps(message))
        time.sleep(1)  # Attendre 1 seconde pour s'assurer que le message est envoyé
        sio.disconnect()
        return

    if internal_msg == None:
        log.error("Missing internal eml file")
        message = {
            "event": "satus",
            "data": "Pièce jointe eml manquante: {}",
        }
        sio.emit("status", json.dumps(message))
        time.sleep(1)  # Attendre 1 seconde pour s'assurer que le message est envoyé
        sio.disconnect()
        return

    # Call the parse_eml function
    try:
        message = {"event": "satus", "data": "Analyse de la pièce jointe eml"}
        sio.emit("status", json.dumps(message))
        (
            subject_field,
            observables_header,
            observables_body,
            attachments,
            hashes_attachments,
            eml_file_tuple,
        ) = parse_eml(internal_msg, sio)
    except Exception as e:
        log.error(
            "Error while trying to parse the internal eml file: {}".format(
                traceback.format_exc()
            )
        )
        message = {
            "event": "satus",
            "data": "Erreur lors de l'analyse de la pièce jointe eml: {}".format(
                traceback.format_exc()
            ),
        }
        sio.emit("status", json.dumps(message))
        time.sleep(1)  # Attendre 1 seconde pour s'assurer que le message est envoyé
        sio.disconnect()
        return

    # Call the create_case function
    try:
        message = {"event": "satus", "data": "Création du cas The Hive"}
        sio.emit("status", json.dumps(message))
        new_case = create_case(
            subject_field,
            observables_header,
            observables_body,
            attachments,
            hashes_attachments,
            eml_file_tuple,
            sio,
        )
    except Exception as e:
        log.error(
            "Error while trying to create the case: {}".format(traceback.format_exc())
        )
        message = {
            "event": "satus",
            "data": "Erreur lors de la création du cas The Hive {}".format(
                traceback.format_exc()
            ),
        }
        sio.emit("status", json.dumps(message))
        time.sleep(1)  # Attendre 1 seconde pour s'assurer que le message est envoyé
        sio.disconnect()
        return

    run_analysis(new_case, external_from_field, sio)

    time.sleep(1)  # Attendre 1 seconde pour s'assurer que le message est envoyé
    sio.disconnect()

    return new_case, external_from_field


if __name__ == "__main__":
    mail_uid = str(sys.argv[1])
    port = str(sys.argv[2])
    main(mail_uid, port)
