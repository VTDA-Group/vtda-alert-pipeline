import os, glob, shutil
import antares_client
from astropy.coordinates import SkyCoord
from astropy import units as u
from astro_ghost.ghostHelperFunctions import getTransientHosts
import marshmallow

from django.conf import settings
from django.db import IntegrityError
from django.shortcuts import get_object_or_404

from tom_antares.antares import get_tag_choices
from tom_targets.models import Target

from custom_code.models import TargetAux

superphot_types = ['SN Ia', 'SN II', 'SN IIn', 'SLSN', 'SN Ibc']
tns_label_dict = {'SN Ia':'Ia', 'SN II':'II', 'SN IIn': 'IIn', 'SLSN': 'SLSN', 'SN Ibc': 'Ibc'}

STATIC_DIR = settings.STATICFILES_DIRS[0]
GHOST_PATH = os.path.join(STATIC_DIR, "ghost")
DATA_DIR = settings.MEDIA_ROOT
TMP_ASSOCIATION_DIR = os.path.join(DATA_DIR, "ghost-temp/")

def extra_antares_tags():
    """Includes all tags of interest that are not shown by ANTARES API but are
    implemented on the ANTARES website."""
    tags = [{'type': 'tag', 'attributes': {'filter_version_id': 1, 'description': 'A hard-coded test.'}, 'id': 'LAISS_RFC_AD_filter', 'file': {'self': './'}},
    {'type': 'tag', 'attributes': {'filter_version_id': 1, 'description': 'A hard-coded test.'}, 'id': 'superphot_plus_classified', 'file': {'self': './'}}]
    return tags


def all_antares_tag_choices():
    """Combine built-in ANTARES tags with extra hard-coded tags."""
    choices = get_tag_choices()
    for s in extra_antares_tags():
        choices.append((s['id'], s['id']))
    return choices
 
    
def get_sn_types():
    """Return list of supernova type choices for the Project form."""
    sn_type_selection = [(s, s) for s in superphot_types]
    sn_type_selection.append(('None','None'))
    return sn_type_selection


def check_type_tns(locus, sn_type):
    sn_type = 'SN '+sn_type
    if 'tns_public_objects' not in locus.catalogs:
        return False
    if 'type' not in locus.catalog_objects['tns_public_objects'][0]:
        return False
    print(locus.catalog_objects['tns_public_objects'][0]['type'], sn_type)
    return locus.catalog_objects['tns_public_objects'][0]['type'] == sn_type


def save_alerts_to_group(project, broker):
    """Save list of alerts' targets along
    with a certain group tag."""
    MAX_ALERTS = 20
    query = project.queryset.generate_antares_query()
    print(query)
    loci = antares_client.search.search(query)
    sn_type = project.sn_type[2:-2] # TODO: fix this
    tns = project.tns
    # TODO: make this not atrocious, will be fixed when query string is not
    #directly saved to model

    tag_objs = project.queryset.tags.all()
    tags = [tag_obj.antares_name for tag_obj in tag_objs]

    n_alerts = 0
    while n_alerts < MAX_ALERTS:
        try:
            locus = next(loci)
        except (marshmallow.exceptions.ValidationError, StopIteration):
            print("no more loci")
            break

        #bandaid solution
        # TODO: fix
        if sn_type not in ['None', '']:
            skippy = True
            if tns and check_type_tns(locus, tns_label_dict[sn_type]):
                skippy = False
            if ('superphot_plus_class' in locus.properties) & ('superphot_plus_classified' in tags):
                if locus.properties['superphot_plus_class'] == sn_type:
                    skippy = False
            if skippy:
                continue

        alert = broker.alert_to_dict(locus)
        try:
            target, _, aliases = broker.to_target(alert)
            target.save(names=aliases)
            target_aux = TargetAux.create(
                target=target, add_host=False
            )
            broker.process_reduced_data(target)

        except IntegrityError:
            print('Target already in database.')
            target = get_object_or_404(
                Target,
                name=alert['properties']['ztf_object_id']
            )
        try:
            project.targets.add(target)
            n_alerts += 1   
        except:
            print('Error saving target to project')
            
            
            
def update_all_hosts():
    """Requeries all targets without hosts."""
    names = []
    coords = []
    for i, target in enumerate(Target.objects.all()):
        try:
            # only requery those without hosts
            if target.aux_info.host is None:
                names.append(target.name)
                print(target.name, target.ra, target.dec)

                coords.append(
                    SkyCoord(
                        ra=target.ra*u.degree,
                        dec=target.dec*u.degree,
                        frame='icrs'
                    )
                )
        except:
            target_aux = TargetAux.create(
                target = target,
                add_host = False
            )
            names.append(target.name)
            print(target.name, target.ra, target.dec)

            coords.append(
                SkyCoord(
                    ra=target.ra*u.degree,
                    dec=target.dec*u.degree,
                    frame='icrs'
                )
            )
            
    print(names, coords)
    hostDB = getTransientHosts(
        transientName=names,
        snCoord=coords,
        snClass=['']*len(coords),
        savepath=TMP_ASSOCIATION_DIR,
        GHOSTpath=GHOST_PATH,
        redo_search=False,
        verbose=1
    )
    
    # delete temp directory
    association_dirs = glob.glob(os.path.join(TMP_ASSOCIATION_DIR, "*"))
    for association_dir in association_dirs:
        shutil.rmtree(association_dir)
    
    for i in range(len(hostDB)):
        try:
            host_row = hostDB.iloc[i]
            target = get_object_or_404(Target, name=host_row['TransientName'])
            target.aux_info._add_host_from_df_row(host_row)
        except: # TO DO: handle transient name changing (add to target aliases)
            continue
        
    
    
    
            
    