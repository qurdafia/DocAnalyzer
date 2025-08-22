# gemini_project/config.py
import os
from dotenv import load_dotenv

load_dotenv('../env')

# --- Vault Configuration ---
# Reads the Vault address from an environment variable, defaulting to the local dev server.
VAULT_ADDR = os.getenv('VAULT_ADDR')

# Reads the Vault token for the backend service. For dev, this can be the root token.
# In production, this should be a token with limited privileges obtained via a secure auth method like AppRole.
VAULT_TOKEN = os.getenv('VAULT_TOKEN')