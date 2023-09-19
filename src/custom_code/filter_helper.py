from tom_antares.antares import get_tag_choices


superphot_types = ['SN Ia', 'SN II', 'SN IIn', 'SLSN', 'SN Ibc']
tns_label_dict = {'SN Ia':'Ia', 'SN II':'II', 'SN IIn': 'IIn', 'SLSN': 'SLSN', 'SN Ibc': 'Ibc'}


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
    
    
def run_anomaly_tag(self, locus):
    """Check if object is considered an anomaly."""
    return locus.properties['LAISS_RFC_anomaly_score'] > 25


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