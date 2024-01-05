import glob
import subprocess


def get_all_filters():
    """Get list of all filters"""
    filters = []
    filter_fn_list = glob.glob("./filters/*.py")
    for filter_fn in filter_fn_list:
        filter_obj = subprocess.run(["python", filter_fn])
        filters.append(filter_obj)
    return filters
