# gemini_project/vault_utils.py
import hvac
from .config import VAULT_ADDR, VAULT_TOKEN

class VaultClient:
    """
    A client to securely fetch secrets from Hashicorp Vault.
    """
    def __init__(self):
        self.client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
        if not self.client.is_authenticated():
            raise Exception("Vault authentication failed. Check VAULT_ADDR and VAULT_TOKEN.")

    # --- UPDATED FUNCTION ---
    def get_secret(self, secret_path, secret_key, mount_point='kv'):
        """
        Fetches a specific key from a secret path in Vault's KVv2 engine,
        allowing for a custom mount point.
        """
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=secret_path,
                mount_point=mount_point # Pass the custom mount point here
            )
            return response['data']['data'][secret_key]
        except (hvac.exceptions.InvalidPath, KeyError) as e:
            print(f"ERROR: Could not find secret '{secret_key}' at path '{secret_path}' on mount point '{mount_point}'. Error: {e}")
            return None

# Create a single, reusable instance for the application
vault_client = VaultClient()