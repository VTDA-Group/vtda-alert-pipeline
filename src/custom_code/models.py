from django.db import models
from tom_common.hooks import run_hook
from tom_targets.models import models, Target
# Create your models here.

class ProjectTargetList(models.Model):
    """
    Class representing a list of targets for a specific project in a TOM.

    :param name: The name of the target list
    :type name: str

    :param targets: Set of ``Target`` objects associated with this ``TargetList``

    :param created: The time at which this target list was created.
    :type created: datetime

    :param modified: The time at which this target list was modified in the TOM database.
    :type modified: datetime
    """
    name = models.CharField(max_length=200, help_text='The name of the Project.')
    targets = models.ManyToManyField(Target)
    created = models.DateTimeField(
        auto_now_add=True, help_text='The time which this target list was created in the TOM database.'
    )
    modified = models.DateTimeField(
        auto_now=True, verbose_name='Last Modified',
        help_text='The time which this target list was changed in the TOM database.'
    )

    class Meta:
        ordering = ('-created', 'name',)

    def __str__(self):
        return self.name