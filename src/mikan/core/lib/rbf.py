# coding: utf-8
"""
Refactored RBF interpolator based on:
https://github.com/mathLab/PyGeM/blob/master/pygem/rbf_factory.py

Performs RBF interpolation with several kernel options.
"""

try:
    import numpy as np

    HAS_NUMPY = True
except:
    HAS_NUMPY = False

__all__ = ['RBF']


class RBF(object):

    @staticmethod
    def get_coefficients(centers, centers_targets, target_values, radius=1.0, regularization=1e-8, kernel_mode=0):
        """
        Computes RBF interpolation coefficients (theta) for given centers and target values.

        Parameters:
        - centers: Nx3 array, input points (P)
        - centers_targets: Mx3 array, RBF centers (X)
        - target_values: Mx3 array, output vectors at centers (Y)
        - radius: float, kernel scale (σ)
        - regularization: float, small diagonal term to avoid singularity
        - kernel_mode: int, selects kernel type (0 = identity, 1 = Gaussian, ...)

        Returns:
        - theta: (N+4)x3 matrix of interpolation weights
        """
        if not HAS_NUMPY:
            raise ImportError("This class requires NumPy. Please install it using 'pip install numpy'.")

        n_input = len(centers)
        n_centers = len(centers_targets)

        P = np.array(centers)  # Shape: N x 3
        X = np.array(centers_targets)  # Shape: M x 3
        Y = np.array(target_values)  # Shape: M x 3

        # Compute pairwise distance matrix between centers and inputs
        distance_matrix = compute_pairwise_distances(X, P)  # Shape: M x N

        if kernel_mode != 0:
            distance_matrix = apply_rbf_kernel(distance_matrix, radius, kernel_mode)

        # Add affine term
        affine_block = np.insert(P, 0, 1, axis=1)  # Add constant 1 as bias term (Shape: N x 4)

        # Build interpolation matrix
        interpolation_matrix = np.zeros((n_input + 4, n_centers + 4))
        interpolation_matrix[:n_input, :n_centers] = distance_matrix
        interpolation_matrix[:n_input, n_centers:] = affine_block
        interpolation_matrix[n_input:, :n_centers] = affine_block.T

        # Right-hand side
        rhs = np.zeros((n_input + 4, 3))
        rhs[:n_input, :] = Y

        # Regularized least-squares solve: theta = (AᵀA + λI)⁻¹ Aᵀ y
        regularizer = np.identity(n_input + 4) * regularization
        A_T = interpolation_matrix.T
        lhs = np.dot(A_T, interpolation_matrix) + regularizer
        pseudo_inv = np.linalg.pinv(lhs)
        theta = np.dot(np.dot(pseudo_inv, A_T), rhs)

        return theta

    @staticmethod
    def evaluate(query_points, centers, coefficients, radius=1.0, kernel_mode=0):
        """
        Evaluate the RBF interpolator at new points.

        Parameters:
        - query_points: Lx3 array of new input points
        - centers: Mx3 array of RBF centers
        - coefficients: (M+4)x3 coefficient matrix from get_coefficients
        - radius: float, kernel scale
        - kernel_mode: int, kernel type

        Returns:
        - interpolated_values: Lx3 array of predicted values
        """
        if not HAS_NUMPY:
            raise ImportError("This class requires NumPy. Please install it using 'pip install numpy'.")

        n_query = len(query_points)
        n_centers = len(centers)

        Q = np.array(query_points)
        C = np.array(centers)

        distance_matrix = compute_pairwise_distances(C, Q)  # Shape: M x L

        if kernel_mode != 0:
            distance_matrix = apply_rbf_kernel(distance_matrix, radius, kernel_mode)

        affine_block = np.insert(C, 0, 1, axis=1)  # Shape: M x 4

        evaluation_matrix = np.zeros((n_centers, n_query + 4))
        evaluation_matrix[:, :n_query] = distance_matrix
        evaluation_matrix[:, n_query:] = affine_block

        interpolated_values = np.dot(evaluation_matrix, coefficients)
        return interpolated_values.reshape(n_centers, 3)


# --- Utility Functions --- #

def compute_pairwise_distances(x, y):
    """
    Efficient Euclidean distance matrix between points in x and y.

    Parameters:
    - x: Nx3 array
    - y: Mx3 array

    Returns:
    - dist_matrix: NxM array of distances
    """
    x = np.array(x)
    y = np.array(y)
    npts_x = x.shape[0]
    npts_y = y.shape[0]

    expander_x = np.ones((1, npts_y, 3))
    expander_y = np.ones((npts_x, 1, 3))

    x_exp = np.expand_dims(x, 1)  # Shape: N x 1 x 3
    y_exp = np.expand_dims(y, 0)  # Shape: 1 x M x 3

    diff = -x_exp * expander_x + y_exp * expander_y
    dist_matrix = np.sqrt(np.sum(diff ** 2, axis=2))

    return dist_matrix


def apply_rbf_kernel(dist, radius, mode):
    """
    Apply selected RBF kernel function to a distance matrix.

    Parameters:
    - dist: distance matrix
    - radius: scale parameter
    - mode: kernel type selector

    Returns:
    - transformed matrix
    """
    if mode == 1:
        return gaussian_rbf(dist, radius)
    elif mode == 2:
        return thin_plate_rbf(dist, radius)
    elif mode == 3:
        return multi_quad_rbf(dist, radius)
    elif mode == 4:
        return inv_multi_quad_rbf(dist, radius)
    elif mode == 5:
        return beckert_wendland_c2_rbf(dist, radius)
    elif mode == 6:
        return compact_rbf(dist, radius)
    else:
        return dist


# --- RBF Kernel Functions --- #

def gaussian_rbf(d, r):
    return np.exp(-(d ** 2) / (2.0 * (0.707 * r) ** 2))


def thin_plate_rbf(d, r):
    v = d / r
    return np.where(v > 0, v ** 2 * np.log(v), 0)


def multi_quad_rbf(d, r):
    return np.sqrt(d ** 2 + r ** 2)


def inv_multi_quad_rbf(d, r):
    return 1.0 / np.sqrt(d ** 2 + r ** 2)


def beckert_wendland_c2_rbf(d, r):
    q = d / r
    mask = (1 - q > 0)
    poly = np.power(1 - q, 4) * ((4 * q) + 1)
    return np.where(mask, poly, 0)


def compact_rbf(d, r):
    h = d / r
    d_clip = np.clip(1 - h, 0, 1)
    return d_clip ** 2
