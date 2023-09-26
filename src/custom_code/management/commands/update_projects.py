from django.core.management.base import BaseCommand
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse

from tom_alerts.alerts import get_service_class, get_service_classes
from tom_observations.models import ObservationRecord

from custom_code.filter_helper import (
    save_alerts_to_group,
    update_all_hosts,
)
from custom_code.models import (
    ProjectTargetList,
)

class ProjectUpdateCommand(BaseCommand):

    help = 'Performs an automatic nightly requery for all existing projects.'

    def handle(self, *args, **options):
        
        broker_name = 'ANTARES' # hard-coded for now
        broker = get_service_class(broker_name)()
        
        for project in ProjectTargetList.objects.all():
            save_alerts_to_group(project, broker)
                    
        update_all_hosts()
        
        return 'Success!'