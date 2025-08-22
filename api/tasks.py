import os
import json
import time
import requests
import certifi
import base64
from celery import shared_task
from django.conf import settings

# --- Constants ---
ABBYY_BASE_URL = "https://vantage-us.abbyy.com"

# --- ABBYY JSON Parser ---
def parse_abbyy_response(raw_data):
    """
    Parses the verbose JSON from ABBYY Vantage and extracts only the
    clean field names and their values.
    """
    clean_data = {}
    try:
        fields = raw_data['Transaction']['Documents'][0]['ExtractedData']['RootObject']['Fields']
        for field in fields:
            field_name = field.get('Name')
            field_list = field.get('List')
            if not field_name or not field_list:
                continue
            
            if field_name == 'techSpecs':
                clean_data[field_name] = []
                for row in field_list:
                    row_data = {}
                    row_columns = row.get('Value', {}).get('Fields', [])
                    for column in row_columns:
                        column_name = column.get('Name')
                        column_list = column.get('List')
                        if column_name and column_list:
                            row_data[column_name] = column_list[0].get('Value')
                    if row_data:
                        clean_data[field_name].append(row_data)
            else:
                clean_data[field_name] = field_list[0].get('Value')
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error parsing ABBYY response: {e}")
        return {"error": "Failed to parse the ABBYY JSON structure."}
    return clean_data

# --- Helper Functions for ABBYY API V1 Workflow ---
def get_abbyy_access_token():
    """Step 1: Authenticate and get an access token."""
    auth_url = f"{ABBYY_BASE_URL}/auth2/connect/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {
        'grant_type': 'client_credentials',
        'client_id': settings.ABBYY_CLIENT_ID,
        'client_secret': settings.ABBYY_CLIENT_SECRET,
        'scope': 'openid permissions global.wildcard'
    }
    response = requests.post(auth_url, headers=headers, data=payload, verify=False)
    response.raise_for_status()
    return response.json()['access_token']

def create_abbyy_transaction(access_token, skill_id):
    """Step 2: Create an empty transaction."""
    url = f"{ABBYY_BASE_URL}/api/publicapi/v1/transactions"
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    body = {'skillId': skill_id}
    response = requests.post(url, headers=headers, json=body, verify=False)
    response.raise_for_status()
    return response.json()['transactionId']

def add_file_to_transaction(access_token, transaction_id, file_content, file_name, content_type):
    """Step 3: Add the file to the created transaction."""
    url = f"{ABBYY_BASE_URL}/api/publicapi/v1/transactions/{transaction_id}/files"
    headers = {'Authorization': f'Bearer {access_token}'}
    files = {'file': (file_name, file_content, content_type)}
    response = requests.post(url, headers=headers, files=files, verify=False)
    response.raise_for_status()

def start_abbyy_transaction(access_token, transaction_id):
    """Step 4: Start the transaction to begin processing."""
    url = f"{ABBYY_BASE_URL}/api/publicapi/v1/transactions/{transaction_id}/start"
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.post(url, headers=headers, json={}, verify=False)
    response.raise_for_status()

def poll_and_get_abbyy_result(access_token, transaction_id):
    """Step 5: Poll for the result and download the final data."""
    status_url = f"{ABBYY_BASE_URL}/api/publicapi/v1/transactions/{transaction_id}"
    headers = {'Authorization': f'Bearer {access_token}'}
    for _ in range(30):
        response = requests.get(status_url, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        status = data.get('status')
        if status == 'Processed':
            file_id = data['documents'][0]['resultFiles'][0]['fileId']
            download_url = f"{ABBYY_BASE_URL}/api/publicapi/v1/transactions/{transaction_id}/files/{file_id}/download"
            result_response = requests.get(download_url, headers=headers, verify=False)
            result_response.raise_for_status()
            return result_response.json()
        elif status in ['Error', 'Cancelled', 'ProcessingFailed']:
            raise Exception(f"ABBYY processing failed with status: {status}")
        time.sleep(5)
    raise Exception("ABBYY processing timed out.")

# --- The Main Celery Task ---
@shared_task(bind=True)
def process_document_analysis(self, file_content_b64, file_name, content_type, manual_rag_text):
    file_content = base64.b64decode(file_content_b64)

    try:
        # ABBYY Workflow
        token = get_abbyy_access_token()
        transaction_id = create_abbyy_transaction(token, settings.ABBYY_SKILL_ID)
        add_file_to_transaction(token, transaction_id, file_content, file_name, content_type)
        start_abbyy_transaction(token, transaction_id)
        raw_abbyy_data = poll_and_get_abbyy_result(token, transaction_id)
        extracted_data = parse_abbyy_response(raw_abbyy_data)
        print(extracted_data)

    except Exception as e:
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise

    try:
        # Gemini Workflow
        model_name = "gemini-1.5-flash-latest"
        # model_name = "gemini-2.5-pro"
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        prompt = f"""
        Act as a senior solutions architect or manager. Based on the tender specifications and additional context below, generate a detailed proposal.
        **Information Extracted from Tender Document:**
        ```json
        {json.dumps(extracted_data, indent=2)}
        ```
        **Additional User Context:**
        "{manual_rag_text}"

        Return the response as a single, valid JSON object that strictly follows this schema:
        {{
            "proposal": {{
                "title": "string",
                "introduction": "string",
                "analysis": {{
                    "data_relevance": "string",
                    "data_quality": "string",
                    "limitations": "string"
                }},
                "proposed_solution": {{
                    "methodology": "string",
                    "steps": ["string", "string"],
                    "technology": "string"
                }},
                "budget": {{ "cost": "string" }},
                "conclusion": "string"
            }}
        }}
        """

        gemini_data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
            }
        }
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": settings.GEMINI_API_KEY
        }

        gemini_response = requests.post(gemini_url, headers=headers, json=gemini_data, verify=False)
        gemini_response.raise_for_status()
        response_data = gemini_response.json()

        if not response_data.get('candidates'):
            block_reason = response_data.get('promptFeedback', {}).get('blockReason', 'Unknown')
            raise ValueError(f"The response from Gemini was blocked due to safety settings. Reason: {block_reason}")

        generated_text = response_data['candidates'][0]['content']['parts'][0]['text']
        cleaned_json_string = generated_text.strip()
        
        if not cleaned_json_string:
            raise ValueError("Gemini returned an empty text response after cleaning.")

        return json.loads(cleaned_json_string)
        
    except Exception as e:
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_message += f" | Response: {e.response.text}"
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': error_message})
        raise