# gemini_project/settings.py
from pathlib import Path
from .vault_utils import vault_client

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Fetch secrets dynamically from Hashicorp Vault ---
SECRET_PATH = 'kv' 
SECRET_KEY = vault_client.get_secret(SECRET_PATH, 'django_secret_key') # Store Django's secret key in Vault too!
ABBYY_CLIENT_ID = vault_client.get_secret(SECRET_PATH, 'abbyy_client_id')
ABBYY_CLIENT_SECRET = vault_client.get_secret(SECRET_PATH, 'abbyy_client_secret')
GEMINI_API_KEY = vault_client.get_secret(SECRET_PATH, 'gemini_api_key')

DEBUG = True
ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'rest_framework',
    'corsheaders',
    'django_celery_results',
    # Your apps
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', # CORS Middleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ... (rest of standard settings.py file)

# Allow your React frontend to communicate with Django
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'