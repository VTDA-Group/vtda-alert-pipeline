from django.urls import path

from custom_code.views import (
    RequeryBrokerView,
    ProjectView,
    ProjectsView,
    ProjectCreateView,
    ProjectDeleteView,
    TargetDetailView,
    ProjectEditView,
)

app_name = 'custom_code'

urlpatterns = [
    path('targets/project/', ProjectView.as_view(), name='project'),
    path('targets/projects/<int:pk>/edit/', ProjectEditView.as_view(), name='edit-project'),
    path('targets/requery_broker/', RequeryBrokerView.as_view(), name='requery-broker'),
    path('targets/projects/', ProjectsView.as_view(), name='projects'),
    path('targets/projects/create-project/', ProjectCreateView.as_view(), name='create-project'),
    path('targets/projects/<int:pk>/delete/', ProjectDeleteView.as_view(), name='delete-project'),
    path('targets/<int:pk>/', TargetDetailView.as_view(), name='detail'),
]
