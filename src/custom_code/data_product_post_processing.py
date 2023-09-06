import numpy as np
from tom_base.tom_common.hooks import target_post_save
from filter_base import run, get_all_filters

def target_post_save_custom(target, created):
    """Custom post-save workflow for target."""
    target_post_save(target, created) # run any TOM-general post-processing
    for f in get_all_filters():
        print(f.name)
        f.run(target)
    
    