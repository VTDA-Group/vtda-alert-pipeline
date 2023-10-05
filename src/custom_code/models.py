from django.db import models
from django.db.models.constraints import CheckConstraint
from django.db.models import Q
from django.db.models import OneToOneField
from django.conf import settings

import os, shutil, glob
import pandas as pd
import re
from astropy.coordinates import SkyCoord
from astropy import units as u
import numpy as np
import requests
from PIL import Image
from io import BytesIO


from astro_ghost.ghostHelperFunctions import (
    findNewHosts,
    getcolorim,
    geturl
)
from astroquery.ipac.ned import Ned

from tom_common.hooks import run_hook
from tom_targets.models import Target, TargetList
from tom_dataproducts.models import ReducedDatum

STATIC_DIR = settings.STATICFILES_DIRS[0]
DATA_DIR = settings.MEDIA_ROOT
GHOST_CSV = os.path.join(STATIC_DIR, "ghost/database/GHOST.csv")
TMP_IMAGE_DIR = os.path.join(DATA_DIR, "tmp/host-images/")
TMP_ASSOCIATION_DIR = os.path.join(DATA_DIR, "ghost-temp/")

    
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
        
        
    @classmethod
    def create(cls, ID, name, ra, dec):
        obj = cls(
            ID=ID,
            name=name,
            ra=ra,
            dec=dec
        )
        obj.save()
        return obj
    
        
    def targets(self):
        return [x.target for x in self.aux_objects.all()]
        
    def add_image(self, filters="grizy"):
        """Get color image of host galaxy.
        """
        url = geturl(self.ra,self.dec,filters=filters,format="png",color=True, type='stack')
        r = requests.get(url)
        im = Image.open(BytesIO(r.content))
        return im     
    
    def add_spectra(self):
        """Get spectra (list) of host galaxy,
        if available, and save as ReducedDatum objects.
        """
        
        try:
            spectra = Ned.get_spectra(self.name)
            
            spec_data = []
            for spectrum in spectra:
                arr = spectrum[0].data.astype('float')
                header = spectrum[0].header

                flux = list(arr[0])
                flux_err = list(arr[2])

                wv0 = 10**header["COEFF0"]
                delta_wv = 10**header["COEFF1"]
                wv = [wv0 + i*delta_wv for i in range(len(flux))]
                spec_data.append([wv, flux, flux_err])
                
            return spec_data

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

    
class TargetAux(models.Model):
    """OneToOne buddy of Target to add HostGalaxy
    ForeignKey and related info.
    """
    host = models.ForeignKey(
        HostGalaxy,
        on_delete=models.SET_NULL,
        null=True,
        related_name="aux_objects"
    )
    host_offset = models.FloatField(
        help_text='Angular offset between target and host galaxy.',
        null=True
    )
    target = OneToOneField(
        Target,
        on_delete=models.CASCADE,
        related_name="aux_info"
    )
    
    @classmethod
    def create(cls, target, add_host=True):
        obj = cls(target=target)
        if add_host:
            obj.search_for_host_galaxy()
        obj.save()
        return obj
    
    def _add_host_from_df_row(self, host):
        host_id = host['objID']
        host_name = host['NED_name']
        host_ra = host['raMean']
        host_dec = host['decMean']
        host_obj = HostGalaxy.create(
            ID = host_id,
            name = host_name,
            ra = host_ra,
            dec = host_dec,
        )
        self.host = host_obj
        self.save()
            
    def search_for_host_galaxy(self):
        """Search for and add host galaxy info.
        """
        fullTable = pd.read_csv(GHOST_CSV)
        host=None
        
        # search by transient name
        transientName = re.sub(r"\s+", "", str(self.target.name))
        possibleNames = [transientName, transientName.upper(), transientName.lower(), "SN"+transientName]
        for name in possibleNames:
            if len(fullTable[fullTable['TransientName'] == name])>0:
                host = fullTable[fullTable['TransientName'] == name].iloc[0]
                return self._add_host_from_df_row(host)
        
        # search by transient coord
        ra, dec = self.target.ra, self.target.dec
        transientCoord = SkyCoord(ra=ra*u.degree, dec=dec*u.degree, frame='icrs')
        smallTable = fullTable[np.abs(fullTable['TransientRA'] - transientCoord.ra.degree)<0.1]
        smallTable = smallTable[np.abs(smallTable['TransientDEC'] - transientCoord.dec.degree)<0.1]
        if len(smallTable) > 0:
            c2 = SkyCoord(
                smallTable['TransientRA'].values*u.deg,
                smallTable['TransientDEC'].values*u.deg,
                frame='icrs'
            )
            sep = np.array(transientCoord.separation(c2).arcsec)
            if np.nanmin(sep) <= 1:
                host_idx = np.where(sep == np.nanmin(sep))[0][0]
                host = smallTable.iloc[host_idx]
                return self._add_host_from_df_row(host)
            
        # search manually
        findNewHosts(
            [self.target.name,],
            [transientCoord,],
            ['',],
            savepath=TMP_ASSOCIATION_DIR
        )
        association_dir = glob.glob(os.path.join(TMP_ASSOCIATION_DIR, "*"))[0]
        association_fn = glob.glob(
            os.path.join(association_dir, "*/FinalAssociationTable.csv")
        )[0]
        
        association_df = pd.read_csv(association_fn)
        # delete temp folder
        shutil.rmtree(association_dir)
        
        if len(association_df) > 0:
            host = association_df.iloc[0]
            return self._add_host_from_df_row(host)
        return None
    

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

    tns = models.BooleanField(
        help_text="Whether to query TNS catalog"
    )
    sn_type = models.CharField(
        max_length=100, help_text="The supernova type to check for."
    )

    
    #class Meta:
    #    ordering = ('-created', 'name',)

    def __str__(self):
        return self.name
    
    
class QuerySet(models.Model):
    """Set of query properties and tags.
    """
    name = models.CharField(
        max_length=100,
        help_text="The query name"
    )
    project = models.OneToOneField(
        ProjectTargetList, on_delete=models.CASCADE
    )
    
    def generate_antares_query(self):
        """Generate ANTARES query string from
        properties and tags.
        """
        props = self.properties.all()
        tags = self.tags.all()
        
        # TODO: allow for ORs (at moment it's all ANDs)
        query = {
            "query": {
                "bool": {
                    "must": []
                }
            }
        }
        for prop in props:
            query["query"]["bool"]["must"].append(
                prop.generate_antares_query_dict()
            )
        for tag in tags:
            query["query"]["bool"]["must"].append(
                tag.generate_antares_query_dict()
            )
        return query


class QueryProperty(models.Model):
    """Class representing a property to restrict during a query. 
    """
    antares_name = models.CharField(
        max_length=100,
        help_text="The property name when queried from ANTARES"
    )
    min_value = models.FloatField(
        help_text="Minimum value",
        null=True,
    )
    max_value = models.FloatField(
        help_text="Maximum value",
        null=True,
    )
    categorical = models.BooleanField(
        help_text="Whether property value is categorical (as opposed to continuous)",
        default=False,  
    )
    # TODO: allow multiple target values in future
    target_value = models.CharField(
        max_length=100,
        help_text="Target property value if categorical",
        null=True,
    )
    queryset = models.ForeignKey(
        QuerySet, on_delete=models.CASCADE,
        related_name='properties'
    )
    
    class Meta: # assert no repeat properties per QuerySet
        constraints = [
            models.UniqueConstraint(
                fields=['queryset', 'antares_name'],
                name='no_repeat_query_properties'
            )
        ]
        
    def generate_antares_query_dict(self):
        """Generate query snippet for property.
        """
        if self.categorical:
            query_dict = {
                "match": {
                    f"properties.{self.antares_name}": self.target_value
                }
            }
        else:
            sub_dict = {}
            
            if self.min_value is not None:
                sub_dict['gte'] = self.min_value
            if self.max_value is not None:
                sub_dict['lte'] = self.max_value
                
            if self.antares_name in ["ra", "dec"]: # why are they named differently :((((
                query_dict = {
                    "range": {
                        f"{self.antares_name}": sub_dict
                    }
                }
            else:
                query_dict = {
                    "range": {
                        f"properties.{self.antares_name}": sub_dict
                    }
                }
        return query_dict
    
    
class QueryTag(models.Model):
    """Class representing a tag to restrict during a query. 
    """
    antares_name = models.CharField(
        max_length=100,
        help_text="The tag name when queried from ANTARES"
    )
    queryset = models.ForeignKey(
        QuerySet, on_delete=models.CASCADE,
        related_name='tags'
    )
    
    class Meta: # assert no repeat properties per QuerySet
        constraints = [
            models.UniqueConstraint(
                fields=['queryset', 'antares_name'],
                name='no_repeat_query_tags'
            )
        ]
        
    def generate_antares_query_dict(self):
        """Generate query snippet for property.
        """
        query_dict = {
            "term": {
                "tags": f"{self.antares_name}"
            }
        }       
        return query_dict

