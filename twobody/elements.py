# Standard library
import abc

# Third-party
import astropy.coordinates as coord
from astropy.constants import G
from astropy.time import Time
import astropy.units as u
import numpy as np
from numpy import pi

# Project
from .transforms import a_m_to_P, P_m_to_a
from .units import UnitSystem

__all__ = ['OrbitalElements', 'KeplerElements', 'TwoBodyKeplerElements']


class ElementsMeta(abc.ABCMeta):

    def __new__(mcls, name, bases, members):

        if 'names' not in members:
            raise ValueError('OrbitalElements subclasses must contain a '
                             'defined class attribute "names" that specified '
                             'the string names of the elements.')

        for name_ in members['names']:
            mcls.readonly_prop_factory(members, name_)

        return super().__new__(mcls, name, bases, members)

    @staticmethod
    def readonly_prop_factory(members, attr_name):
        def getter(self):
            return self.units.decompose(getattr(self, '_' + attr_name))
        members[attr_name] = property(getter)


class OrbitalElements(metaclass=ElementsMeta):
    """
    Subclasses must define the class attribute ``.default_units`` to be a
    ``UnitSystem`` instance.
    """

    names = []

    def __init__(self, units):

        # Make sure the units specified are a UnitSystem instance
        if units is None:
            units = self.default_units

        elif units is not None and not isinstance(units, UnitSystem):
            units = UnitSystem(*units)

        self.units = units

        # Now make sure all element name attributes have been set:
        for name in self.names:
            if not hasattr(self, '_'+name):
                raise AttributeError('Invalid class definition!')


class KeplerElements(OrbitalElements):

    default_units = UnitSystem(u.au, u.day, u.Msun, u.degree, u.km/u.s)
    names = ['P', 'a', 'e', 'omega', 'i', 'Omega', 'M0']

    @u.quantity_input(P=u.year, a=u.au,
                      omega=u.deg, i=u.deg, Omega=u.deg, M0=u.deg)
    def __init__(self, *, P=None, a=None,
                 e=0, omega=None, i=None, Omega=None,
                 M0=None, t0=None, units=None):
        """Keplerian orbital elements.

        Parameters
        ----------
        P : quantity_like [time]
            Orbital period.
        a : quantity_like [length] (optional)
            Semi-major axis. If unspecified, computed orbits will be unscaled.
        e : numeric (optional)
            Orbital eccentricity. Default is circular, ``e=0``.
        omega : quantity_like, `~astropy.coordinates.Angle` [angle]
            Argument of pericenter.
        i : quantity_like, `~astropy.coordinates.Angle` [angle]
            Inclination of the orbit.
        Omega : quantity_like, `~astropy.coordinates.Angle` [angle]
            Longitude of the ascending node.
        M0 : quantity_like, `~astropy.coordinates.Angle` [angle] (optional)
            Mean anomaly at epoch ``t0``. Default is 0º if not specified.
        t0 : numeric, `~astropy.coordinates.Time` (optional)
            Reference epoch. Default is J2000 if not specified.
        units : `~twobody.units.UnitSystem`, iterable (optional)
            The unit system to represent quantities in. The default unit system
            is accessible as `KeplerElements.default_units`.

        """

        if M0 is None:
            # Default phase at reference epoch is 0º
            M0 = 0 * u.degree

        if t0 is None:
            # Default reference epoch is J2000
            t0 = Time('J2000')

        if not isinstance(t0, Time):
            # If a number is specified, assume it is Barycentric MJD
            t0 = Time(t0, format='mjd', scale='tcb')

        # Now check that required elements are defined:
        _required = ['P', 'omega', 'i', 'Omega']
        for name in _required:
            if eval(name) is None:
                raise ValueError("You must specify {0}.".format(name))

        # Value validation:
        if P < 0*u.day:
            raise ValueError("Period `P` must be positive.")

        if a is not None and a < 0*u.au:
            raise ValueError("Semi-major axis `a` must be positive.")

        if e < 0 or e >= 1:
            raise ValueError("Eccentricity `e` must be: 0 <= e < 1")

        if i < 0*u.deg or i > 180*u.deg:
            raise ValueError("Inclination `i` must be between 0º and 180º, you "
                             "passed in i={:.3f}".format(i.to(u.degree)))

        # Set object attributes, but make them read-only
        self._a = a if a is not None else 1.*u.dimensionless_unscaled
        self._P = P
        self._e = float(e) * u.dimensionless_unscaled
        self._omega = coord.Angle(omega).wrap_at(360*u.deg)
        self._i = coord.Angle(i)
        self._Omega = coord.Angle(Omega).wrap_at(360*u.deg)
        self._M0 = coord.Angle(M0)
        self.t0 = t0

        # Must happen at the end because it validates that all element names
        # have been set properly:
        super().__init__(units=units)

    @property
    def K(self):
        """Velocity semi-amplitude."""
        K = 2*pi * self.a * np.sin(self.i) / (self.P * np.sqrt(1-self.e**2))
        return self.units.decompose(K)

    @property
    def m_f(self):
        """Binary mass function."""
        return self.units.decompose(self.P * self.K**3 / (2*pi * G))

    # Python builtins
    def __repr__(self):
        return ("<KeplerElements [P={:.2f}, a={:.2f}, e={:.2f}, "
                "ω={:.2f}, i={:.2f}, Ω={:.2f}]>"
                .format(self.P, self.a, self.e, self.omega, self.i, self.Omega))


# TODO: be very explicit. Are we specifying the elements of one of the bodies,
# or of the fictitious body? Or allow user to specify?
class TwoBodyKeplerElements(KeplerElements):

    names = ['P', 'a', 'e', 'm1', 'm2', 'omega', 'i', 'Omega', 'M0']

    @u.quantity_input(a=u.au, P=u.year, m1=u.Msun, m2=u.Msun,
                      omega=u.deg, i=u.deg, Omega=u.deg, M0=u.deg)
    def __init__(self, *, a=None, P=None, m1=None, m2=None,
                 e=None, omega=None, i=None, Omega=None,
                 M0=None, t0=None, units=None):

        if m1 is None or m2 is None:
            raise ValueError("You must specify m1 and m2.")

        if P is None:
            P = a_m_to_P(a, m1+m2).to(u.day)

        if a is None:
            a = P_m_to_a(P, m1+m2).to(u.au)

        super().__init__(a=a, P=P,
                         e=e, omega=omega, i=i, Omega=omega,
                         M0=M0, t0=t0, units=units)

        self.m1 = m1
        self.m2 = m2
        self.m_tot = self.m1 + self.m2

    def get_component(self, num):
        """TODO
        """
        num = str(num)

        if num == '1':
            a = self.m2 / self.m_tot * self.a
            omega = self.omega

        elif num == '2':
            a = self.m1 / self.m_tot * self.a
            omega = self.omega + np.pi*u.radian

        else:
            raise ValueError("Invalid input '{0}' - must be '1' or '2'"
                             .format(num))

        return KeplerElements(a=a, P=self.P,
                              e=self.e, omega=omega, i=self.i, Omega=self.Omega,
                              M0=self.M0, t0=self.t0)

    @property
    def primary(self):
        return self.get_component('1')

    @property
    def secondary(self):
        return self.get_component('2')

    # Python builtins
    def __repr__(self):
        return ("<TwoBodyKeplerElements [m1={:.2f}, m2={:.2f}, "
                "P={:.2f}, a={:.2f}, e={:.2f}, "
                "ω={:.2f}, i={:.2f}, Ω={:.2f}]>"
                .format(self.m1, self.m2, self.P, self.a, self.e,
                        self.omega, self.i, self.Omega))
