# gemini_project/celery.py
import sys
import eventlet

# --- THE FIX ---
# This code checks if the command used to start the program was the 'celery' command.
# It applies the monkey patch ONLY for the Celery worker, not for the Django server.
if 'celery' in sys.argv[0]:
    eventlet.monkey_patch()

import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gemini_project.settings')

app = Celery('gemini_project')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()