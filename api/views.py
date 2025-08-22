# api/views.py
import base64
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from celery.result import AsyncResult
from .tasks import process_document_analysis
from .permissions import IsVaultAuthenticated

class FullAnalysisView(APIView):
    """Starts the asynchronous document analysis task."""
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsVaultAuthenticated]

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('document')
        rag_text = request.data.get('ragText', '')

        if not uploaded_file:
            return Response({"error": "No document provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Encode file content to base64 to pass to Celery
        file_content_b64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
        
        task = process_document_analysis.delay(
            file_content_b64, 
            uploaded_file.name, 
            uploaded_file.content_type, 
            rag_text
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