from django.urls import path

from custom_code.views import RequeryBrokerView
app_name = 'custom_code'

urlpatterns = [
    path('targets/requery_broker/', RequeryBrokerView.as_view(), name='requery-broker'),
    path('targets/projects/', RequeryBrokerView.as_view(), name='projects'),

]