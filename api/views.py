# api/views.py
import base64
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from celery.result import AsyncResult
from .tasks import process_document_analysis
from .permissions import IsVaultAuthenticated

# api/views.py
import yaml
from pathlib import Path
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny # No authentication needed for this


# --- Add a view to provide configuration to the frontend ---
class ConfigView(APIView):
    permission_classes = [AllowAny] # Anyone can access this config

    def get(self, request, *args, **kwargs):
        config_path = Path(settings.BASE_DIR) / 'config.yaml'
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            return Response(config_data)
        except FileNotFoundError:
            return Response({"error": "Configuration file not found."}, status=500)
        

class FullAnalysisView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsVaultAuthenticated]

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('document')
        rag_text = request.data.get('ragText', '')
        # Get the new parameters from the request
        doc_type_id = request.data.get('doc_type_id')
        model_id = request.data.get('model_id')

        if not all([uploaded_file, doc_type_id, model_id]):
            return Response({"error": "Missing required fields: document, doc_type_id, model_id"}, status=status.HTTP_400_BAD_REQUEST)
        
        file_content_b64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
        
        # Pass the new parameters to the Celery task
        task = process_document_analysis.delay(
            file_content_b64, 
            uploaded_file.name, 
            uploaded_file.content_type, 
            rag_text,
            doc_type_id,
            model_id
        )

        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)


class TaskStatusView(APIView):
    """Checks the status of a Celery task."""
    permission_classes = [IsVaultAuthenticated]

    def get(self, request, task_id, *args, **kwargs):
        task_result = AsyncResult(task_id)
        
        if task_result.failed():
            # Access the custom error message if available
            error_info = task_result.info if isinstance(task_result.info, dict) else str(task_result.info)
            result = {"status": task_result.status, "error": error_info}
        else:
            result = {"status": task_result.status, "result": task_result.result}
            
        return Response(result, status=status.HTTP_200_OK)