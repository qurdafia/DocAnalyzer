import base64
import json
import yaml
import requests
from pathlib import Path
from celery import shared_task
from django.conf import settings
from gemini_project.vault_utils import vault_client

# Import Providers
from .abbyy_provider import AbbyyProvider
from .llm_providers.gemini_provider import GeminiProvider
from .llm_providers.openai_provider import OpenAIProvider

from .utils import parse_abbyy_response # <-- Import from utils

# --- ABBYY JSON Parser ---
ABBYY_BASE_URL = "https://vantage-us.abbyy.com"


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


# Provider Factory
def get_llm_provider(provider_name, model_id, config):
    provider_info = config['providers'][provider_name]
    
    # Use the new, separated path keys from the config
    mount_point = provider_info['vault_mount_point']
    secret_path = provider_info['vault_secret_path']
    api_key_vault_key = provider_info['api_key_vault_key']
    
    api_key = vault_client.get_secret(secret_path, api_key_vault_key, mount_point=mount_point)

    if provider_name == "google":
        return GeminiProvider(api_key, model_id, config['api_endpoints']['google_gemini'])
    elif provider_name == "openai":
        return OpenAIProvider(api_key, model_id)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
    
# The Main Orchestrator Task
@shared_task(bind=True)
def process_document_analysis(self, file_content_b64, file_name, content_type, manual_rag_text, doc_type_id, model_id):
    # 1. Load Configuration
    config_path = Path(settings.BASE_DIR) / 'config.yaml'
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    doc_type_config = next((item for item in config_data['document_types'] if item['id'] == doc_type_id), None)
    model_config = next((item for item in config_data['ai_models'] if item['id'] == model_id), None)
    
    if not doc_type_config or not model_config:
        raise ValueError("Invalid document type or model ID.")
    
    file_content = base64.b64decode(file_content_b64)

    # 2. ABBYY Workflow
    try:
        abbyy_provider = AbbyyProvider(config_data, vault_client)
        token = abbyy_provider.get_access_token()
        transaction_id = abbyy_provider.create_transaction(token, doc_type_config['abbyy_skill_id'])
        abbyy_provider.add_file_to_transaction(token, transaction_id, file_content, file_name, content_type)
        abbyy_provider.start_transaction(token, transaction_id)
        raw_abbyy_data = abbyy_provider.poll_and_get_result(token, transaction_id)
        extracted_data = parse_abbyy_response(raw_abbyy_data)
    except Exception as e:
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise

    # 3. LLM Workflow
    try:
        llm_provider = get_llm_provider(model_config['provider'], model_id, config_data)
        
        prompt_template_path = Path(settings.BASE_DIR) / doc_type_config['prompt_template']
        with open(prompt_template_path, 'r') as f:
            prompt_template = f.read()
        prompt = prompt_template.format(extracted_data=json.dumps(extracted_data, indent=2), manual_rag_text=manual_rag_text)
        
        final_json = llm_provider.generate_analysis(prompt)
        return final_json
    except Exception as e:
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_message += f" | Response: {e.response.text}"
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': error_message})
        raise