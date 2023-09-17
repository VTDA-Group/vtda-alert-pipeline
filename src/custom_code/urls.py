from django.urls import path

from custom_code.views import (
    RequeryBrokerView,
    ProjectView,
    ProjectCreateView
)

app_name = 'custom_code'

urlpatterns = [
    path('targets/requery_broker/', RequeryBrokerView.as_view(), name='requery-broker'),
    path('targets/projects/', ProjectView.as_view(), name='projects'),
    path('targets/projects/create-project/', ProjectCreateView.as_view(), name='create-project')

]