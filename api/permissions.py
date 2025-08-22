# api/permissions.py
from rest_framework.permissions import BasePermission
from gemini_project.vault_utils import vault_client
import hvac.exceptions # Import the hvac exceptions module

class IsVaultAuthenticated(BasePermission):
    """
    Checks if the request includes a valid Vault token in the header.
    """
    def has_permission(self, request, view):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return False
            
        token = auth_header.split(' ')[1]
        if not token:
            return False
            
        try:
            # --- CORRECTED LOGIC ---
            # The validation is simple: if the lookup API call succeeds, the token is valid.
            # If the token were invalid, the hvac library would raise an exception.
            vault_client.client.auth.token.lookup(token)
            
            # If we reach this line, it means no exception was raised, so the token is good.
            return True

        except hvac.exceptions.InvalidRequest:
            # This exception is typically raised for invalid or expired tokens.
            print("--- DEBUG: Vault rejected the token as invalid. ---")
            return False
        except Exception as e:
            # This will catch other errors, like network issues.
            print(f"--- DEBUG: An unexpected error occurred during token lookup: {e} ---")
            return False