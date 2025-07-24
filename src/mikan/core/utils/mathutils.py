# coding: utf-8

from math import floor, log10, sqrt, cos, sin, acos, asin
from functools import reduce

from mikan.vendor.geomdl import BSpline
from mikan.vendor.geomdl.linalg import vector_normalize
from mikan.vendor.geomdl.utilities import generate_knot_vector

__all__ = [
    'fexp', 'fman',
    'lerp', 'ease_in_quad', 'ease_out_quad', 'ease_in_out_quad',
    'ease_in_cubic', 'ease_out_cubic', 'ease_in_out_cubic',
    'cubic_solve', 'bspline',
    'eigh',
    'SplineRemap', 'NurbsCurveRemap', 'NurbsSurfaceRemap'
]


# ----- decimal

def fexp(f):
    return int(floor(log10(abs(f)))) if f != 0 else 0


def fman(f):
    return f / 10 ** fexp(f)


# ----- interpolations


def lerp(a, b, w):
    return a * (1 - w) + b * w


# t: current time, x (start at 0)
# b: start value, y0 (usually 0)
# c: change in value, height (usually 1)
# d: duration, length (usually 1)

# t: t -> t+d
# v: b -> b+c


def ease_in_quad(t, b, c, d):
    t /= float(d)
    return c * t * t + b


def ease_out_quad(t, b, c, d):
    t /= float(d)
    return -c * t * (t - 2) + b


def ease_in_out_quad(t, b, c, d):
    t /= d / 2.
    if t < 1:
        return c / 2. * t * t + b
    t -= 1
    return -c / 2. * (t * (t - 2) - 1) + b


def ease_in_cubic(t, b, c, d):
    t /= float(d)
    return c * t * t * t + b


def ease_out_cubic(t, b, c, d):
    t /= float(d)
    t -= 1
    return c * (t * t * t + 1) + b


def ease_in_out_cubic(t, b, c, d):
    t /= d / 2.
    if t < 1:
        return c / 2. * t * t * t + b
    t -= 2
    return c / 2. * (t * t * t + 2) + b


def cubic_solve(a, b, c, d):
    """
    Main Function takes in the coefficient of the Cubic Polynomial as parameters and it returns the roots.
    Polynomial Structure -> ax^3 + bx^2 + cx + d = 0
    """

    if a == 0 and b == 0:  # liner equation
        return [(-d * 1.0) / c]  # linear root

    elif a == 0:  # quadratic equations
        D = c * c - 4.0 * b * d
        if D >= 0:
            D = sqrt(D)
            x1 = (-c + D) / (2.0 * b)
            x2 = (-c - D) / (2.0 * b)
        else:
            D = sqrt(-D)
            x1 = (-c + D * 1j) / (2.0 * b)
            x2 = (-c - D * 1j) / (2.0 * b)

        return [x1, x2]  # quadratic roots

    f = ((3.0 * c / a) - ((b ** 2.0) / (a ** 2.0))) / 3.0
    g = (((2.0 * (b ** 3.0)) / (a ** 3.0)) - ((9.0 * b * c) / (a ** 2.0)) + (27.0 * d / a)) / 27.0
    h = (g ** 2.0) / 4.0 + (f ** 3.0) / 27.0

    if f == 0 and g == 0 and h == 0:
        if (d / a) >= 0:
            x = (d / (1.0 * a)) ** (1 / 3.0) * -1
        else:
            x = (-d / (1.0 * a)) ** (1 / 3.0)
        return [x, x, x]  # equal roots

    elif h <= 0:
        i = sqrt(((g ** 2.0) / 4.0) - h)
        j = i ** (1 / 3.0)
        k = acos(-(g / (2 * i)))
        L = j * -1
        M = cos(k / 3.0)
        N = sqrt(3) * sin(k / 3.0)
        P = (b / (3.0 * a)) * -1

        x1 = 2 * j * cos(k / 3.0) - (b / (3.0 * a))
        x2 = L * (M + N) + P
        x3 = L * (M - N) + P

        return [x1, x2, x3]  # real roots

    elif h > 0:
        R = -(g / 2.0) + sqrt(h)
        if R >= 0:
            S = R ** (1 / 3.0)
        else:
            S = (-R) ** (1 / 3.0) * -1
        T = -(g / 2.0) - sqrt(h)
        if T >= 0:
            U = (T ** (1 / 3.0))
        else:
            U = ((-T) ** (1 / 3.0)) * -1

        x1 = (S + U) - (b / (3.0 * a))
        x2 = -(S + U) / 2 - (b / (3.0 * a)) + (S - U) * sqrt(3) * 0.5j
        x3 = -(S + U) / 2 - (b / (3.0 * a)) - (S - U) * sqrt(3) * 0.5j

        return [x1, x2, x3]  # one real root and two complex roots


def bspline(k, m, u, knots):
    s = 0.0
    if m == 1:
        return knots[k] < u and u <= knots[k + 1]
    d1 = knots[k + m - 1] - knots[k]
    if d1 != 0:
        s = (u - knots[k]) * bspline(k, m - 1, u, knots) / d1
    d2 = knots[k + m] - knots[k + 1]
    if d2 != 0:
        s += (knots[k + m] - u) * bspline(k + 1, m - 1, u, knots) / d2
    return s


# ----- eigen values

def eigh(a, tol=1.0e-9):
    """
    Calculates the eigenValues and vectors using jacobi method.
    Code configured without numpy from http://goo.gl/U3m7nX

    Returns:
        (list of 3 floats) EigenValues
        (3x3 list of floats) EigenVectors
    """

    # find largest off-diag. element a[k][l]
    def max_elem(a):
        n = len(a)
        a_max = 0.0
        for i in range(n - 1):
            for j in range(i + 1, n):
                if abs(a[i][j]) >= a_max:
                    a_max = abs(a[i][j])
                    k = i
                    l = j
        return a_max, k, l

    # Rotate to make a[k][l] = 0
    def rotate(a, p, k, l):
        n = len(a)
        a_diff = a[l][l] - a[k][k]
        if abs(a[k][l]) < abs(a_diff) * 1.0e-36:
            t = a[k][l] / a_diff
        else:
            phi = a_diff / (2.0 * a[k][l])
            t = 1.0 / (abs(phi) + sqrt(phi ** 2 + 1.0))
            if phi < 0.0:
                t = -t
        c = 1.0 / sqrt(t ** 2 + 1.0)
        s = t * c
        tau = s / (1.0 + c)
        temp = a[k][l]
        a[k][l] = 0.0
        a[k][k] = a[k][k] - t * temp
        a[l][l] = a[l][l] + t * temp
        for i in range(k):  # Case of i < k
            temp = a[i][k]
            a[i][k] = temp - s * (a[i][l] + tau * temp)
            a[i][l] = a[i][l] + s * (temp - tau * a[i][l])
        for i in range(k + 1, l):  # Case of k < i < l
            temp = a[k][i]
            a[k][i] = temp - s * (a[i][l] + tau * a[k][i])
            a[i][l] = a[i][l] + s * (temp - tau * a[i][l])
        for i in range(l + 1, n):  # Case of i > l
            temp = a[k][i]
            a[k][i] = temp - s * (a[l][i] + tau * temp)
            a[l][i] = a[l][i] + s * (temp - tau * a[l][i])
        for i in range(n):  # Update transformation matrix
            temp = p[i][k]
            p[i][k] = temp - s * (p[i][l] + tau * p[i][k])
            p[i][l] = p[i][l] + s * (temp - tau * p[i][l])

    # Set limit on number of rotations
    n = len(a)
    max_rot = 5 * (n ** 2)

    p = [[1.0, 0.0, 0.0],
         [0.0, 1.0, 0.0],
         [0.0, 0.0, 1.0]]

    # Jacobi rotation loop
    for i in range(max_rot):
        a_max, k, l = max_elem(a)
        if a_max < tol:
            return [a[i][i] for i in range(len(a))], p

        rotate(a, p, k, l)


class SplineRemap(object):
    def __init__(self, input, output):

        cps = list(zip(input, output))
        self.sum = []

        for i in range(len(cps) - 1):
            ps = []

            # left tan
            if i == 0:
                ps += [cps[0], cps[0]]
            else:
                tan = [cps[i + 1][0] - cps[i - 1][0], cps[i + 1][1] - cps[i - 1][1]]
                tan = vector_normalize(tan)
                k = (cps[i + 1][0] - cps[i][0]) / 3
                k *= 1. / tan[0]
                tan = [k * tan[0], k * tan[1]]

                ps.append(cps[i])
                ps.append([cps[i][0] + tan[0], cps[i][1] + tan[0]])

            # right tan
            if i == len(cps) - 2:
                ps += [cps[-1], cps[-1]]
            else:
                tan = [cps[i + 1][0] - cps[i - 1][0], cps[i + 1][1] - cps[i - 1][1]]
                tan = vector_normalize(tan)
                k = (cps[i + 1][0] - cps[i][0]) / 3
                k *= 1. / tan[0]
                tan = [k * tan[0], k * tan[1]]

                ps.append([cps[i + 1][0] - tan[0], cps[i + 1][1] - tan[1]])
                ps.append(cps[i + 1])

            self.sum.append(ps)

    def get(self, x):

        for s in self.sum:
            if s[0][0] <= x <= s[3][0]:
                p = s
                break
        else:
            raise RuntimeError('x not in interval')

        a = -p[0][0] + 3 * p[1][0] - 3 * p[2][0] + p[3][0]
        b = 3 * p[0][0] - 6 * p[1][0] + 3 * p[2][0]
        c = -3 * p[0][0] + 3 * p[1][0]
        d = p[0][0] - x
        roots = cubic_solve(a, b, c, d)

        for u in roots:
            if isinstance(u, complex):
                continue
            if 0 <= u <= 1:
                return p[0][1] * (1 - u) ** 3 + 3 * p[1][1] * u * (1 - u) ** 2 + 3 * p[2][1] * u ** 2 * (1 - u) + p[3][1] * u ** 3

        return p[0][1]


class NurbsCurveRemap(object):
    def __init__(self, n, degree=3, periodic=False):

        self.periodic = periodic
        self.curves = []
        for i in range(n):
            curve = BSpline.Curve()
            curve.degree = degree
            cps = [[0, 0] for x in range(n)]
            cps[i] = [1, 0]
            if periodic:
                cps += cps[:degree]
            curve.ctrlpts = cps

            if not periodic:
                curve.knotvector = generate_knot_vector(curve.degree, len(curve.ctrlpts))
            else:
                knots = [x for x in range(len(cps) + degree + 1)]
                curve.knotvector = knots

            self.curves.append(curve)

    def get(self, u):

        curve = self.curves[0]
        if self.periodic:
            start = curve.knotvector[curve.degree]
            stop = curve.knotvector[-(curve.degree + 1)]
            range = stop - start
            u = u * range + start

        result = []
        for curve in self.curves:
            result.append(curve.evaluate_single(u)[0])
        return result


class NurbsSurfaceRemap(object):
    def __init__(self, nu, nv, degree=(3, 3), periodic=(False, False)):
        self.periodic = periodic
        self.surfs = []
        for i in range(nu * nv):
            surf = BSpline.Surface()
            surf.degree_u = degree[0]
            surf.degree_v = degree[1]

            u_lines = []
            j = 0
            for v in range(nv):
                u_line = []
                for u in range(nu):
                    if i == j:
                        u_line.append([1, 0])
                    else:
                        u_line.append([0, 0])
                    j += 1
                u_lines.append(u_line)

            v_lines = list(zip(*u_lines))
            if periodic[0]:
                v_lines += v_lines[:degree[0]]
            cps = []
            for v_line in v_lines:
                if periodic[1]:
                    v_line += v_line[:degree[1]]
                cps += v_line

            _nu = nu
            _nv = nv
            if periodic[0]:
                _nu += degree[0]
            if periodic[1]:
                _nv += degree[1]

            surf.set_ctrlpts(cps, _nu, _nv)

            if not periodic[0]:
                surf.knotvector_u = generate_knot_vector(surf.degree_u, nu)
            else:
                surf.knotvector_u = [x for x in range(nu + degree[0] + degree[0] + 1)]

            if not periodic[1]:
                surf.knotvector_v = generate_knot_vector(surf.degree_v, nv)
            else:
                surf.knotvector_v = [x for x in range(nv + degree[1] + degree[1] + 1)]

            self.surfs.append(surf)

    def get(self, u, v):
        surf = self.surfs[0]
        if self.periodic[0]:
            start = surf.knotvector_u[surf.degree_u]
            stop = surf.knotvector_u[-(surf.degree_u + 1)]
            range = stop - start
            u = u * range + start
        if self.periodic[1]:
            start = surf.knotvector_v[surf.degree_v]
            stop = surf.knotvector_v[-(surf.degree_v + 1)]
            range = stop - start
            v = v * range + start

        result = []
        for surf in self.surfs:
            result.append(surf.evaluate_single((u, v))[0])
        return result


def find_greatest_common_divisor(a, b, rtol=1e-05, atol=1e-08):
    t = min(abs(a), abs(b))
    while abs(b) > rtol * t + atol:
        a, b = b, a % b
    return a


def find_greatest_common_divisor_from_list(list, rtol=1e-05, atol=1e-08):
    def find_greatest_common_divisor_modif(a, b):
        return find_greatest_common_divisor(a, b, rtol, atol)

    x = reduce(find_greatest_common_divisor_modif, list)
    return x
