from custom_code.filters.filter_helper import get_all_filters


def target_post_save(target, created):
    """Custom post-save workflow for target."""
    for f in get_all_filters():
        print(f.name)
        f.run(target)
