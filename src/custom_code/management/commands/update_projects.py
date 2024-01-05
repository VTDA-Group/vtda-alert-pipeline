from django.core.management.base import BaseCommand
from tom_alerts.alerts import get_service_class

from custom_code.filter_helper import (
    save_alerts_to_group,
    update_all_hosts,
)
from custom_code.models import (
    ProjectTargetList,
)


class Command(BaseCommand):
    help = 'Performs an automatic nightly requery for all existing projects.'

    def handle(self, *args, **options):
        broker_name = 'ANTARES'  # hard-coded for now
        broker = get_service_class(broker_name)()

        for project in ProjectTargetList.objects.all():
            save_alerts_to_group(project, broker)

        update_all_hosts()
        self.stdout.write(self.style.SUCCESS('Successfully updated all existing projects.'))
