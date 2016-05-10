# Licensed under a 3-clause BSD style license - see LICENSE.rst

from __future__ import print_function, division, absolute_import

import numpy as np
from matplotlib.patches import Polygon

from astropy import units as u
from astropy.coordinates.representation import UnitSphericalRepresentation, CartesianRepresentation
from astropy.coordinates.angles import rotation_matrix

__all__ = ['SphericalCircle']


def _transform_cartesian(representation, matrix):

    # Get xyz once since it's an expensive operation
    xyz = representation.xyz

    # Since the underlying data can be n-dimensional, reshape to a
    # 2-dimensional (3, N) array.
    vec = xyz.reshape((3, xyz.size // 3))

    # Do the transformation
    vec_new = np.dot(np.asarray(matrix), vec)

    # Reshape to preserve the original shape
    subshape = xyz.shape[1:]
    x = vec_new[0].reshape(subshape)
    y = vec_new[1].reshape(subshape)
    z = vec_new[2].reshape(subshape)

    # Make a new representation and return
    return CartesianRepresentation(x, y, z)


def _rotate_polygon(lon, lat, lon0, lat0):
    """
    Given a polygon with vertices defined by (lon, lat), rotate the polygon
    such that the North pole of the spherical coordinates is now at (lon0,
    lat0). Therefore, to end up with a polygon centered on (lon0, lat0), the
    polygon should initially be drawn around the North pole.
    """

    # Create a representation object
    polygon = UnitSphericalRepresentation(lon=lon, lat=lat)

    # Determine rotation matrix to make it so that the circle is centered
    # on the correct longitude/latitude.
    m1 = rotation_matrix(-(0.5 * np.pi * u.radian - lat0), axis='y')
    m2 = rotation_matrix(-lon0, axis='z')
    transform_matrix = m2 * m1

    # Apply 3D rotation
    polygon = polygon.to_cartesian()

    try:
        polygon = polygon.transform(transform_matrix)
    except:  # TODO: remove once Astropy 1.1 is no longer supported
        polygon = _transform_cartesian(polygon, transform_matrix)

    polygon = UnitSphericalRepresentation.from_cartesian(polygon)

    return polygon.lon, polygon.lat


class SphericalCircle(Polygon):
    """
    Create a patch representing a spherical circle - that is, a circle that is
    formed of all the points that are within a certain angle of the central
    coordinates on a sphere. Here we assume that latitude goes from -90 to +90

    This class is needed in cases where the user wants to add a circular patch
    to a celestial image, since otherwise the circle will be distorted, because
    a fixed interval in longitude corresponds to a different angle on the sky
    depending on the latitude.

    Parameters
    ----------
    center : tuple or `~astropy.units.Quantity`
        This can be either a tuple of two `~astropy.units.Quantity` objects, or
        a single `~astropy.units.Quantity` array with two elements.
    radius : `~astropy.units.Quantity`
        The radius of the circle
    resolution : int, optional
        The number of points that make up the circle - increase this to get a
        smoother circle.
    vertex_unit : `~astropy.units.Unit`
        The units in which the resulting polygon should be defined.

    Notes
    -----
    Additional keyword arguments are passed to `~matplotlib.patches.Polygon`
    """

    def __init__(self, center, radius, resolution=100, vertex_unit=u.degree, **kwargs):

        # Extract longitude/latitude, either from a tuple of two quantities, or
        # a single 2-element Quantity.
        longitude, latitude = center

        # Start off by generating the circle around the North pole
        lon = np.linspace(0., 2 * np.pi, resolution + 1)[:-1] * u.radian
        lat = np.repeat(0.5 * np.pi - radius.to(u.radian).value, resolution) * u.radian

        lon, lat = _rotate_polygon(lon, lat, longitude, latitude)

        # Extract new longitude/latitude in the requested units
        lon = lon.to(vertex_unit).value
        lat = lat.to(vertex_unit).value

        # Create polygon vertices
        vertices = np.array([lon, lat]).transpose()

        super(SphericalCircle, self).__init__(vertices, **kwargs)
