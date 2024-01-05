import glob
import os
import shutil

import antares_client
import marshmallow
from astro_ghost.ghostHelperFunctions import getTransientHosts
from astropy import units as u
from astropy.coordinates import SkyCoord
from django.conf import settings
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from tom_targets.models import Target

from custom_code.models import TargetAux

superphot_types = ['SN Ia', 'SN II', 'SN IIn', 'SLSN', 'SN Ibc']
tns_label_dict = {'SN Ia': 'Ia', 'SN II': 'II', 'SN IIn': 'IIn', 'SLSN': 'SLSN', 'SN Ibc': 'Ibc'}

STATIC_DIR = settings.STATICFILES_DIRS[0]
GHOST_PATH = os.path.join(STATIC_DIR, "ghost")
DATA_DIR = settings.MEDIA_ROOT
TMP_ASSOCIATION_DIR = os.path.join(DATA_DIR, "ghost-temp/")


def get_sn_types():
    """Return list of supernova type choices for the Project form."""
    sn_type_selection = [(s, s) for s in superphot_types]
    # removed the following line as the behaviour is the same as not selecting any supernova type
    # removal is to prevent users from selecting a supernova type and this as well
    # sn_type_selection.append(('None', 'None'))
    return sn_type_selection


def check_type_tns(locus, sn_type):
    sn_type = 'SN ' + sn_type
    if 'tns_public_objects' not in locus.catalog_objects:
        return False
    if 'type' not in locus.catalog_objects['tns_public_objects'][0]:
        return False
    print(locus.catalog_objects['tns_public_objects'][0]['type'], sn_type)
    return locus.catalog_objects['tns_public_objects'][0]['type'] == sn_type


def save_alerts_to_group(project, broker):
    """Save list of alerts' targets along
    with a certain group tag."""
    print(f"Querying alerts for {project.name}")

    MAX_ALERTS = 20
    query = project.queryset.generate_antares_query()
    print(query)
    loci = antares_client.search.search(query)
    tns = project.tns
    sn_types = project.sn_types.all()

    tag_objs = project.queryset.tags.all()
    tags = [tag_obj.antares_name for tag_obj in tag_objs]

    n_alerts = 0
    while n_alerts < MAX_ALERTS:
        try:
            locus = next(loci)
        except (marshmallow.exceptions.ValidationError, StopIteration):
            print("no more loci")
            break

        if sn_types:
            # user selected some supernova types
            # we will go through the locus and see if such types exist
            # if not, we will skip this locus
            ok = False
            for sn_type in sn_types:
                if (tns and check_type_tns(locus, tns_label_dict[sn_type.sn_type])) \
                        or ('superphot_plus_class' in locus.properties
                            and 'superphot_plus_classified' in tags
                            and locus.properties['superphot_plus_class'] == sn_type.sn_type):
                    ok = True
                    break
            if not ok:
                # this locus does not have the supernova type(s) we want
                # skip this locus
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
    print("Requerying all targets without hosts.")
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
                        ra=target.ra * u.degree,
                        dec=target.dec * u.degree,
                        frame='icrs'
                    )
                )
        except:
            target_aux = TargetAux.create(
                target=target,
                add_host=False
            )
            names.append(target.name)
            print(target.name, target.ra, target.dec)

            coords.append(
                SkyCoord(
                    ra=target.ra * u.degree,
                    dec=target.dec * u.degree,
                    frame='icrs'
                )
            )

    print(names, coords)
    hostDB = getTransientHosts(
        transientName=names,
        snCoord=coords,
        snClass=[''] * len(coords),
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
        except:  # TO DO: handle transient name changing (add to target aliases)
            continue
