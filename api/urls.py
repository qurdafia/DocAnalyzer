# api/urls.py
from django.urls import path
from .views import FullAnalysisView, TaskStatusView, ConfigView

urlpatterns = [
    path('analyze/', FullAnalysisView.as_view(), name='start-analysis'),
    path('task-status/<str:task_id>/', TaskStatusView.as_view(), name='task-status'),
    path('config/', ConfigView.as_view(), name='app-config'),
]