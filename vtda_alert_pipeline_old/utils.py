import numpy as np

def mag_to_flux(m, merr, zp):
    """Convert magnitudes and magnitude errors
    to corresponding fluxes/flux errors.
    """
    f = 10.0 ** (-1.0 * (m - zp) / 2.5)
    ferr = np.log(10.0) / 2.5 * f * merr
    return f, ferr