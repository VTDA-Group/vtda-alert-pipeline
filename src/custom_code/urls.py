from django.urls import path

from custom_code.views import RequeryBrokerView
app_name = 'custom_code'

urlpatterns = [
    path('requery_broker/', RequeryBrokerView.as_view(), name='requery-broker'),

]