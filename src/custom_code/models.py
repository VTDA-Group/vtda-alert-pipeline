from django.db import models
from django.db.models.constraints import CheckConstraint
from django.db.models import Q

from tom_common.hooks import run_hook
from tom_targets.models import models, TargetList
from tom_targets.models import Target as TargetOrig

GHOST_CSV = "data/ghost/GHOST.csv"

class ProjectTargetList(TargetList):
    """
    Class representing a list of targets for a specific project in a TOM.
    Extends the TargetList class.

    :param name: The name of the target list
    :type name: str

    :param targets: Set of ``Target`` objects associated with this ``TargetList``

    :param created: The time at which this target list was created.
    :type created: datetime

    :param modified: The time at which this target list was modified in the TOM database.
    :type modified: datetime
    """
    # Note from Kaylee: apparently in Django you can't override attributes of non-abstract classes!
    # May change TargetList and ProjectTargetList to both inherit from mutual abstract class in future
    #name = models.CharField(max_length=200, help_text='The name of the Project.')

    query = models.CharField(
        max_length=1000, help_text="This project's query submission string for ANTARES."
    )
    tns = models.BooleanField(
        help_text="Whether to query TNS catalog"
    )
    sn_type = models.CharField(
        max_length=100, help_text="The supernova type to check for."
    )

    
    class Meta:
        ordering = ('-created', 'name',)

    def __str__(self):
        return self.name

    
class HostGalaxy(models.Model):
    """Represents a Host Galaxy.
    """
    ID = models.IntegerField(
        help_text="Object ID of galaxy",
        primary_key=True
    )
    name = models.CharField(
        max_length=100,
        help_text="NED name of galaxy",
        unique=True,
    )
    ra = models.FloatField(
        help_text="Right ascension of galaxy",
    )
    dec = models.FloatField(
        help_text="Declination of galaxy",
    )
    catalog = models.CharField(
        max_length=100,
        help_text="CSV file where all columns are stored.",
        default=GHOST_CSV
    )
    
    class Meta:
        constraints = (
            # for checking in the DB
            CheckConstraint(
                check=Q(ra__gte=0.0) & Q(ra__lte=360.0),
                name='host_ra_range'
            ),
            CheckConstraint(
                check=Q(dec__gte=-180.0) & Q(dec__lte=180.0),
                name='host_dec_range'
            ),
        )
        
    def get_image(self, filters="grizy"):
        """Get color image of host galaxy.
        """
        return getcolorim(
            self.ra,
            self.dec,
            filters
        )
    
    def get_spectra(self):
        """Get spectra (list) of host galaxy,
        if available.
        """
        try:
            spectra = Ned.get_spectra(self.name)
            return spectra
        except:
            return None
        
    def query_from_csv(self, columns=None):
        """Query any properties not included in Model
        object from host CSV. If columns is None, return
        entire DataFrame row as dictionary.
        """
        df = pd.read_csv(self.catalog)
        host_df = df[df['NED_name'] == self.name]
        
        if columns is not None:
            return host_df[columns]
        
        return host_df
        
        
    
    
class HostGalaxyName(models.Model):
    """
    Class representing an alternative name for a ``HostGalaxy''.
    """
    host = models.ForeignKey(HostGalaxy, on_delete=models.CASCADE, related_name='aliases')
    name = models.CharField(max_length=100, unique=True, verbose_name='Alias')
    created = models.DateTimeField(
        auto_now_add=True, help_text='The time at which this host name was created.'
    )
    modified = models.DateTimeField(
        auto_now=True, verbose_name='Last Modified',
        help_text='The time at which this host name was changed in the TOM database.'
    )
    def __str__(self):
        return self.name

    def validate_unique(self, *args, **kwargs):
        """
        Ensures that HostGalaxy.name and all aliases of the host are unique.
        Called automatically when checking form.is_valid().
        Should call HostGalaxyName.full_clean() to validate before save.
        """
        super().validate_unique(*args, **kwargs)
        # If nothing has changed for the alias, skip rest of uniqueness validation.
        # We do not want to fail validation for existing objects, only newly added/updated ones.
        if self.pk and self.name == HostGalaxyName.objects.get(pk=self.pk).name:
            # Skip remaining uniqueness validation.
            return

        # If Alias name matches host name, Return error
        if self.name == self.host.name:
            raise ValidationError(f'Alias {self.name} has a conflict with the primary name of the target. '
                                  f'(target_id={self.target.id})')

        # Check DB for similar target/alias names.
        matches = HostGalaxy.matches.check_for_fuzzy_match(self.name)
        if matches:
            raise ValidationError(f'Host with Name or alias similar to {self.name} already exists')


    
class Target(TargetOrig):
    """Override target class to add HostGalaxy
    ForeignKey and related info.
    """
    host = models.ForeignKey(
        HostGalaxy,
        on_delete=models.SET_NULL,
        null=True,
    )
    host_offset = models.FloatField(
        help_text='Angular offset between target and host galaxy.',
        null=True
    )
    
    
    
    
