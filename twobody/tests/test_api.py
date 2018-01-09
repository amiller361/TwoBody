# Third-party
import astropy.coordinates as coord
import astropy.units as u
from astropy.tests.helper import quantity_allclose
import numpy as np

# Project
from ..elements import KeplerElements, TwoBodyKeplerElements

# TwoBody API exploration
# Note: Anything labeled "Future: v2.0" will be implemented later.

# The Elements classes are used to specify orbital elements. Right now, only the
# KeplerElements class exists and is used to specify Keplerian orbital elements.
elem = KeplerElements(a=1.5*u.au, e=0.5, P=1.*u.year,
                      omega=67*u.deg, i=21.*u.deg, Omega=33*u.deg,
                      M0=53*u.deg, t0=59112.1423)

# The elements correspond to a specific orbit, so if this is one component of a
# binary, a actually corresponds to a1.

# In the above, the epoch, t0, is assumed to be MJD if a number is passed in,
# but it can also be specified as an astropy.time.Time object:
import astropy.time as at
t0 = at.Time(2459812.641, format='jd')
elem = KeplerElements(a=1.5*u.au, e=0.5, P=1.*u.year,
                      omega=67*u.deg, i=21.*u.deg, Omega=33*u.deg,
                      M0=53*u.deg, t0=t0)

# If not specified, the epoch is taken to be J2000:
elem = KeplerElements(a=1.5*u.au, e=0.5, P=1.*u.year,
                      omega=67*u.deg, i=21.*u.deg, Omega=33*u.deg, M0=53*u.deg)
assert elem.t0 == at.Time('J2000')

# These classes support transforming the input elements to other common
# parameters within their element system. For example, with any input (see
# above), the following attributes are available for a KeplerElements instance:
elem.P
elem.a
elem.m_f # "binary mass function"
elem.K # velocity semi-amplitude

# To specify orbital elements of a binary or two-body system, use the
# TwoBodyKeplerElements class. With this class, the orbital elements specified
# correspond to the orbit of one of the two bodies in the system. By convention,
# this is usually the more massive "primary" body
# TODO: or should they be the orbital elements of the fictitious particle?
elem = TwoBodyKeplerElements(m1=1*u.Msun, m2=2*u.Msun,
                             a=1.5*u.au, e=0.5,
                             omega=67*u.deg, i=21.*u.deg, Omega=33*u.deg,
                             M0=53*u.deg, t0=59112.1423)

# From this object, we can access the orbital elements of each component orbit
# individually:
elem1 = elem.get_component('1')
elem2 = elem.get_component('2')
# Or, using short-hand names:
# assert elem.primary == elem.get_component('1')
# assert elem.secondary == elem.get_component('2')

assert elem1.__class__ == KeplerElements
assert quantity_allclose(elem1.a,
                         elem.a * elem.m2 / (elem.m1 + elem.m2))
assert quantity_allclose(elem1.omega, elem.omega)
assert quantity_allclose(elem2.omega, elem.omega + np.pi*u.rad)

# We could then create orbit objects for each component in the system:
orb1 = KeplerOrbit(elem.primary)
orb2 = KeplerOrbit(elem.secondary)

# Can also specify P instead of a
elem = TwoBodyKeplerElements(m1=1*u.Msun, m2=2*u.Msun,
                             P=1.*u.year, e=0.5,
                             omega=67*u.deg, i=21.*u.deg, Omega=33*u.deg,
                             M0=53*u.deg, t0=59112.1423)

# Future: v2.0
# - Also support other element parametrizations, e.g., Delaunay variables
#   elem = DelaunayElements(...)

# In the above examples, since we created an Elements instance explicitly, to
# create an Orbit object, we pass the Elements instance in to the KeplerOrbit
# initializer. For example, for a single orbit:
t0 = at.Time(2459812.641, format='jd')
elem = KeplerElements(a=1.5*u.au, e=0.5, P=1.*u.year,
                      omega=67*u.deg, i=21.*u.deg, Omega=33*u.deg,
                      M0=53*u.deg, t0=t0)
orb = KeplerOrbit(elements=elem)
orb = KeplerOrbit(elem)

# We don't have to create an Elements object before creating an orbit. Using the
# string name of the elements class, we can pass the components directly in to
# the KeplerOrbit initializer:
orb = KeplerOrbit(a=1.5*u.au, e=0.5, P=1.*u.year,
                  omega=67*u.deg, i=21.*u.deg, Omega=33*u.deg,
                  M0=53*u.deg, t0=t0,
                  elements_type='kepler') # this is default

# Because 'kepler' is default, this will work:
orb = KeplerOrbit(a=1.5*u.au, e=0.5, P=1.*u.year,
                  omega=67*u.deg, i=21.*u.deg, Omega=33*u.deg,
                  M0=53*u.deg, t0=t0)

# With an orbit instance, we can easily access observable orbital quantities,
# for example, to get the radial velocity of the body (corresponding to `m1`)
time = at.Time([59812.141, 59142.782, 59147.559], format='mjd')
rv = orb.radial_velocity(time)

# If instead we didn't specify any masses, the computed orbital properties [are
# dimensionless TODO?] but can be scaled to a velocity. For example, the radial
# velocity curve can be directly multiplied by a semi-amplitude:
orb = KeplerOrbit(P=1.*u.year, e=0.5,
                  omega=67*u.deg, i=21.*u.deg, Omega=33*u.deg,
                  M0=53*u.deg, t0=t0)
K = 10 * u.m/u.s
rv = K * orb.unscaled_radial_velocity(time)

# Both of these work with astrometric orbits as well:
orb = KeplerOrbit(elements=elem)
icrs = orb.sky_position(time)
icrs = amp * orb.unscaled_sky_position(time)

# TODO:
# Barycenter position and straight-line motion can be specified
bc_frame = coord.ICRS(ra=180.84*u.deg, dec=-11*u.deg, distance=110*u.pc,
                      pm_ra_cosdec=110*u.mas/u.yr, pm_dec=81*u.mas/u.yr,
                      radial_velocity=-17*u.km/u.s)
bc = Barycenter(bc_frame, t0=59117.012)
orb = KeplerOrbit(elements=elem, barycenter=bc)

# TODO: When barycenter motion specified, add v*(t-t0)?? to position - different t from
# RV, different t0??
# - Need 6 more parameters for Barycenter position and velocity at reference
#   epoch - moves on straight line x1 = x0 + v1*t ; v1 = v0

# We can also get out the full phase-space coordinates at each time as an
# Astropy frame object:
# TODO: better name for this?
orbit6d = orb.six_d(time)

# The returned orbit frame object is solar system barycentric but aligned with
# the reference plane coordinates of the orbit. The Cartesian coordinates in
# this frame therefore refer to the (capital) X, Y, Z system of
# Murray & Correira 2010:
XYZ = orbit6d.cartesian.xyz

# Transform the orbit evaluated at the above times to the ICRS frame:
icrs = orbit6d.transform_to(coord.ICRS)

# Sky positions:
icrs.ra, icrs.dec

# Radial velocity:
icrs.radial_velocity

# Get a Cartesian representation of the orbit. Note: this is now ICRS Cartesian!
icrs.cartesian
