import time
from .llm_providers.requests_provider import RequestsProvider

class AbbyyProvider:
    def __init__(self, config, vault_client):
        self.config = config['api_endpoints']['abbyy']
        self.secret_config = config['providers']['abbyy']
        self.vault_client = vault_client
        # --- THIS LINE IS CHANGED ---
        # Initialize the HTTP client with SSL verification turned OFF
        self.http_client = RequestsProvider(verify=False)

    # In api/abbyy_provider.py

    def get_access_token(self):
        # Fetch secrets using the new, separated paths from the config
        mount_point = self.secret_config['vault_mount_point']
        secret_path = self.secret_config['vault_secret_path']

        client_id = self.vault_client.get_secret(
            secret_path,
            self.secret_config['client_id_vault_key'],
            mount_point=mount_point
        )
        client_secret = self.vault_client.get_secret(
            secret_path,
            self.secret_config['client_secret_vault_key'],
            mount_point=mount_point
        )

        if not client_id or not client_secret:
            raise ValueError("ABBYY Client ID or Secret could not be loaded from Vault. Check config.yaml and Vault secrets.")

        auth_url = f"{self.config['base_url']}{self.config['auth_endpoint']}"
        payload = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'openid permissions global.wildcard'
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        response = self.http_client.post(auth_url, headers=headers, data=payload)
        response.raise_for_status()
        return response.json()['access_token']

    def create_transaction(self, access_token, skill_id):
        url = f"{self.config['base_url']}{self.config['transactions_endpoint']}"
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        body = {'skillId': skill_id}
        response = self.http_client.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()['transactionId']

    def add_file_to_transaction(self, access_token, transaction_id, file_content, file_name, content_type):
        url = f"{self.config['base_url']}{self.config['transactions_endpoint']}/{transaction_id}/files"
        headers = {'Authorization': f'Bearer {access_token}'}
        files = {'file': (file_name, file_content, content_type)}
        response = self.http_client.post(url, headers=headers, files=files)
        response.raise_for_status()

    def start_transaction(self, access_token, transaction_id):
        url = f"{self.config['base_url']}{self.config['transactions_endpoint']}/{transaction_id}/start"
        headers = {'Authorization': f'Bearer {access_token}'}
        response = self.http_client.post(url, headers=headers, json={})
        response.raise_for_status()

    def poll_and_get_result(self, access_token, transaction_id):
        status_url = f"{self.config['base_url']}{self.config['transactions_endpoint']}/{transaction_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        for _ in range(30):
            response = self.http_client.get(status_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == 'Processed':
                file_id = data['documents'][0]['resultFiles'][0]['fileId']
                download_url = f"{self.config['base_url']}{self.config['transactions_endpoint']}/{transaction_id}/files/{file_id}/download"
                result_response = self.http_client.get(download_url, headers=headers)
                result_response.raise_for_status()
                return result_response.json()
            elif data.get('status') in ['Error', 'Cancelled', 'ProcessingFailed']:
                raise Exception(f"ABBYY processing failed with status: {data.get('status')}")
            time.sleep(5)
        raise Exception("ABBYY processing timed out.")