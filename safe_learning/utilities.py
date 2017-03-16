"""
Utilities for plotting, function definitions, and GPs.

This file defines utilities needed for the experiments, such as creating
parameter grids, computing LQR controllers, Lyapunov functions, sample
functions of Gaussian processes, and plotting ellipses.

Author: Felix Berkenkamp, Learning & Adaptive Systems Group, ETH Zurich
        (GitHub: befelix)
"""

from __future__ import absolute_import, division, print_function

import numpy as np
import scipy.interpolate
import scipy.linalg
import tensorflow as tf
from functools import wraps

__all__ = ['combinations', 'linearly_spaced_combinations', 'lqr', 'dlqr',
           'ellipse_bounds', 'concatenate_inputs']


def concatenate_inputs(start=0):
    """Concatenate the numpy array inputs to the functions.

    Parameters
    ----------
    start : int, optional
        The attribute number at which to start concatenating.
    """
    def wrap(function):
        @wraps(function)
        def wrapped_function(*args, **kwargs):
            """A function that concatenates inputs."""
            nargs = len(args) - start
            # Check for tensorflow object
            if isinstance(args[start], tf.Tensor):
                # reduce number of function calls in graph
                if nargs == 1:
                    return function(*args, **kwargs)
                # concatenate extra arguments
                args = args[:start] + (tf.concat(args[start:], axis=1),)
                return function(*args, **kwargs)
            else:
                # Map to 2D objects
                to_concatenate = map(np.atleast_2d, args[start:])

                if nargs == 1:
                    concatenated = tuple(to_concatenate)
                else:
                    concatenated = (np.hstack(to_concatenate),)

                args = args[:start] + concatenated
                return function(*args, **kwargs)

        return wrapped_function

    return wrap


def combinations(arrays):
    """Return a single array with combinations of parameters.

    Parameters
    ----------
    arrays : list of np.array

    Returns
    -------
    array : np.array
        An array that contains all combinations of the input arrays
    """
    return np.array(np.meshgrid(*arrays)).T.reshape(-1, len(arrays))


def linearly_spaced_combinations(bounds, num_samples):
    """
    Return 2-D array with all linearly spaced combinations with the bounds.

    Parameters
    ----------
    bounds : sequence of tuples
        The bounds for the variables, [(x1_min, x1_max), (x2_min, x2_max), ...]
    num_samples : integer or array_likem
        Number of samples to use for every dimension. Can be a constant if
        the same number should be used for all, or an array to fine-tune
        precision. Total number of data points is num_samples ** len(bounds).

    Returns
    -------
    combinations : 2-d array
        A 2-d arrray. If d = len(bounds) and l = prod(num_samples) then it
        is of size l x d, that is, every row contains one combination of
        inputs.
    """
    bounds = np.atleast_2d(bounds)
    num_vars = len(bounds)
    num_samples = np.broadcast_to(num_samples, num_vars)

    # Create linearly spaced test inputs
    inputs = [np.linspace(b[0], b[1], n) for b, n in zip(bounds,
                                                         num_samples)]

    # Convert to 2-D array
    return combinations(inputs)


def lqr(a, b, q, r):
    """Compute the continuous time LQR-controller.

    The optimal control input is `u = -k.dot(x)`.

    Parameters
    ----------
    a : np.array
    b : np.array
    q : np.array
    r : np.array

    Returns
    -------
    k : np.array
        Controller matrix
    p : np.array
        Cost to go matrix
    """
    a, b, q, r = map(np.atleast_2d, (a, b, q, r))
    p = scipy.linalg.solve_continuous_are(a, b, q, r)

    # LQR gain
    k = np.linalg.solve(r, b.T.dot(p))

    return k, p


def dlqr(a, b, q, r):
    """Compute the discrete-time LQR controller.

    The optimal control input is `u = -k.dot(x)`.

    Parameters
    ----------
    a : np.array
    b : np.array
    q : np.array
    r : np.array

    Returns
    -------
    k : np.array
        Controller matrix
    p : np.array
        Cost to go matrix
    """
    a, b, q, r = map(np.atleast_2d, (a, b, q, r))
    p = scipy.linalg.solve_discrete_are(a, b, q, r)

    # LQR gain
    tmp1 = np.linalg.multi_dot((b.T, p, b))
    tmp2 = np.linalg.multi_dot((b.T, p, a))
    k = np.linalg.solve(tmp1 + r, tmp2)

    return k, p


def ellipse_bounds(P, level, n=100):
    """Compute the bounds of a 2D ellipse.

    The levelset of the ellipsoid is given by
    level = x' P x. Given the coordinates of the first
    dimension, this function computes the corresponding
    lower and upper values of the second dimension and
    removes any values of x0 that are outside of the ellipse.

    Parameters
    ----------
    P : np.array
        The matrix of the ellipsoid
    level : float
        The value of the levelset
    n : int
        Number of data points

    Returns
    -------
    x : np.array
        1D array of x positions of the ellipse
    yu : np.array
        The upper bound of the ellipse
    yl : np.array
        The lower bound of the ellipse

    Notes
    -----
    This can be used as
    ```plt.fill_between(*ellipse_bounds(P, level))```
    """
    # Round up to multiple of 2
    n += n % 2

    # Principal axes of ellipsoid
    eigval, eigvec = np.linalg.eig(P)
    eigvec *= np.sqrt(level / eigval)

    # set zero angle at maximum x
    angle = np.linspace(0, 2 * np.pi, n)[:, None]
    angle += np.arctan(eigvec[0, 1] / eigvec[0, 0])

    # Compute positions
    pos = np.cos(angle) * eigvec[:, 0] + np.sin(angle) * eigvec[:, 1]
    n /= 2

    # Return x-position (symmetric) and upper/lower bounds
    return pos[:n, 0], pos[:n, 1], pos[:n - 1:-1, 1]
