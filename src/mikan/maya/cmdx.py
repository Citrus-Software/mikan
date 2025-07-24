# coding: utf-8
"""
cmdx monkey patch
"""

from six import iteritems

from mikan.vendor.cmdx import *
from mikan.vendor.cmdx import _encode1, _encodedagpath1

SAFE_MODE = True


# Overrides


def _path(self, full=False):
    """
    Returns a consistent and minimal plug path using the node's shortest path.

    This overrides the default behavior which uses the full node path.
    Using `shortestPath()` makes the result more readable and avoids
    unnecessarily long paths, especially in deep DAG hierarchies.
    """
    return "{}.{}".format(
        self._node.shortestPath(), self._mplug.partialName(
            includeNodeName=False,
            useLongNames=True,
            useFullAttributePath=full
        )
    )


Plug.path = _path

Plug.__repr__ = lambda self: self.path()  # Returns a concise string representation of the plug, using its path.
DagNode.__str__ = lambda self: self.shortestPath()  # Overrides the default `__str__` which returns the full path.
DagNode.__repr__ = DagNode.__str__


# Missing API for DAG node instances.
def _isInstanced(self):
    return self._fn.isInstanced()


DagNode.isInstanced = _isInstanced
if ENABLE_PEP8:
    DagNode.is_instanced = DagNode.isInstanced

# Fixes the default value Maya assigns to boolean plugs
Boolean.Default = False

# Add missing Euler rotation order constants for convenience
Euler.XYZ = kXYZ
Euler.XZY = kXZY
Euler.YXZ = kYXZ
Euler.YZX = kYZX
Euler.ZXY = kZXY
Euler.ZYX = kZYX

# Alias for accessing rotation order from string
Euler.orders = Euler.strToOrder


def _hash(self):
    """
    Returns a stable hash based on the MObject handle.

    This avoids issues with the default path-based hash, which can
    change over time (e.g. after renaming or DAG edits), causing
    problems when used as dictionary keys.
    """
    return om.MObjectHandle(self._mobject).hashCode()


Node.__hash__ = _hash


def clear_instances():
    Singleton._instances.clear()


def _dot(self, value):
    return self * value


def _cross(self, value):
    return Vector(self ^ value)


Vector.dot = _dot
Vector.cross = _cross

# Missing PEP8
Plug.is_array = Plug.isArray
Plug.is_compound = Plug.isCompound


# Node copy/deepcopy

def _copy(self):
    return self


def _deepcopy(self, obj):
    return self


Node.__copy__ = _copy
Node.__deepcopy__ = _deepcopy
Plug.__copy__ = _copy
Plug.__deepcopy__ = _deepcopy


# Custom commands for node interaction

def _decode_object(arg):
    if isinstance(arg, Node):
        return arg.shortest_path()
    elif isinstance(arg, Plug):
        return arg.path(full=False)
    elif isinstance(arg, (list, tuple, dict)):
        return _decode_objects(arg)
    return arg


def _decode_objects(args):
    if isinstance(args, list):
        return list(map(_decode_object, args))
    elif isinstance(args, tuple):
        return tuple(map(_decode_object, args))
    elif isinstance(args, dict):
        d = {}
        for k, v in iteritems(args):
            d[_decode_object(k)] = _decode_object(v)
        return d
    else:
        return _decode_object(args)


decode = _decode_object


def cmd(cmd, *args, **kwargs):
    return cmd(*_decode_objects(args), **_decode_objects(kwargs))


def encode_cmd(cmd, *args, **kwargs):
    res = cmd(*_decode_objects(args), **_decode_objects(kwargs))
    if isinstance(res, string_types):
        return encode(res)
    elif isinstance(res, list):
        return list(map(encode, res))
    elif isinstance(res, tuple):
        return tuple(map(encode, res))
    return res


def encode(path):
    """Convert relative or absolute `path` to cmdx objects
    Fastest conversion from absolute path to Node/Plug/Component
    Arguments:
        path (str): Absolute or relative path to DAG/DG node or plug
    """

    assert isinstance(path, string_types), "%s was not string" % path

    selectionList = om.MSelectionList()

    try:
        selectionList.add(path)
    except RuntimeError:
        raise ExistError("'%s' does not exist" % path)

    mobj = selectionList.getDependNode(0)
    if "." in path:  # costs 0.2µs
        # check whether path is a plug or a component
        try:
            mplug = selectionList.getPlug(0)
            return Plug(Node(mobj), mplug)
        except TypeError:
            # is a component, return node instead
            pass
        except RuntimeError:
            raise ExistError("'%s' does not exist" % path)

    return Node(mobj)


_delete = delete


def delete(*args, **kwargs):
    """
    Wrapper around cmds.delete to address issues observed in earlier cmdx versions.

    In particular, deleting groups of nodes in a hierarchy sometimes caused
    unexpected behavior. This function uses the original Maya command to
    ensure reliable deletion.
    """
    return cmd(cmds.delete, *args, **kwargs)


def ls(*args, **kwargs):
    args = _decode_objects(args)
    return [encode(x) for x in cmds.ls(*args, **kwargs)]


# Add a wider range of node type constants to improve API completeness.
# This extends the available constants with additional Maya node types.

tAddDoubleLinear = om.MTypeId(0x4441444c)
tAddMatrix = om.MTypeId(0x44414d58)
tAimConstraint = om.MTypeId(0x44414d43)
tAngleBetween = om.MTypeId(0x4e414254)
tAngleDimension = om.MTypeId(0x4147444e)
tAnimCurveTA = om.MTypeId(0x50435441)
tAnimCurveTL = om.MTypeId(0x5043544c)
tAnimCurveTT = om.MTypeId(0x50435454)
tAnimCurveTU = om.MTypeId(0x50435455)
tAnimCurveUA = om.MTypeId(0x50435541)
tAnimCurveUL = om.MTypeId(0x5043554c)
tAnimCurveUT = om.MTypeId(0x50435554)
tAnimCurveUU = om.MTypeId(0x50435555)
tBaseLattice = om.MTypeId(0x46424153)
tBezierCurve = om.MTypeId(0x42435256)
tBlendColors = om.MTypeId(0x52424c32)
tBlendTwoAttr = om.MTypeId(0x41424c32)
tBlendShape = om.MTypeId(0x46424c53)
tBlendWeighted = om.MTypeId(0x41424c57)
tComposeMatrix = om.MTypeId(0x58000301)
tCamera = om.MTypeId(0x4443414d)
tChoice = om.MTypeId(0x43484345)
tChooser = om.MTypeId(0x43484f4f)
tClosestPointOnMesh = om.MTypeId(0x43504f4d)
tClosestPointOnSurface = om.MTypeId(0x4e435053)
tCondition = om.MTypeId(0x52434e44)
tClamp = om.MTypeId(0x52434c33)
tCluster = om.MTypeId(0x46434c53)
tCurveInfo = om.MTypeId(0x4e43494e)
tDecomposeMatrix = om.MTypeId(0x58000300)
tDeltaMush = om.MTypeId(0x444c544d)
tDisplayLayer = om.MTypeId(0x4453504c)
tDistanceBetween = om.MTypeId(0x44444254)
tEulerToQuat = om.MTypeId(0x58000080)
tFfd = om.MTypeId(0x46464644)
tFile = om.MTypeId(0x52544654)
tFourByFourMatrix = om.MTypeId(0x4642464d)
tGroupId = om.MTypeId(0x47504944)
tGroupParts = om.MTypeId(0x47525050)
tInverseMatrix = om.MTypeId(0x58000302)
tJoint = om.MTypeId(0x4a4f494e)
tLattice = om.MTypeId(0x464c4154)
tLocator = om.MTypeId(0x4c4f4354)
tLoft = om.MTypeId(0x4e534b4e)
tMesh = om.MTypeId(0x444d5348)
tMotionPath = om.MTypeId(0x4d505448)
tMultiplyDivide = om.MTypeId(0x524d4449)
tMultDoubleLinear = om.MTypeId(0x444d444c)
tMultMatrix = om.MTypeId(0x444d544d)
tMute = om.MTypeId(0x4d555445)
tNearestPointOnCurve = om.MTypeId(0x4e504f43)
tNetwork = om.MTypeId(0x4e54574b)
tNoise = om.MTypeId(0x52544e33)
tNonLinear = om.MTypeId(0x464e4c44)
tNurbsCurve = om.MTypeId(0x4e435256)
tNurbsSurface = om.MTypeId(0x4e535246)
tObjectSet = om.MTypeId(0x4f425354)
tOrientConstraint = om.MTypeId(0x444f5243)
tPairBlend = om.MTypeId(0x4150424c)
tParentConstraint = om.MTypeId(0x44504152)
tPlusMinusAverage = om.MTypeId(0x52504d41)
tPointConstraint = om.MTypeId(0x44505443)
tPointOnCurveInfo = om.MTypeId(0x4e504349)
tPointOnSurfaceInfo = om.MTypeId(0x4e505349)
tPolyEdgeToCurve = om.MTypeId(0x50544356)
tPolySmoothFace = om.MTypeId(0x50534d46)
tQuatToEuler = om.MTypeId(0x58000081)
tRebuildCurve = om.MTypeId(0x4e524243)
tRebuildSurface = om.MTypeId(0x4e524253)
tReference = om.MTypeId(0x5245464e)
tReverse = om.MTypeId(0x52525653)
tSetRange = om.MTypeId(0x52524e47)
tShadingEngine = om.MTypeId(0x53484144)
tShrinkWrap = om.MTypeId(0x53575250)
tSkinCluster = om.MTypeId(0x4653434c)
tSoftMod = om.MTypeId(0x4653534c)
tTime = om.MTypeId(0x54494d45)
tTransform = om.MTypeId(0x5846524d)
tTransformGeometry = om.MTypeId(0x5447454f)
tUnitConversion = om.MTypeId(0x44554e54)
tVectorProduct = om.MTypeId(0x52564543)
tWire = om.MTypeId(0x46574952)
tWrap = om.MTypeId(0x46575250)
tWtAddMatrix = om.MTypeId(0x4457414d)

kAnimCurve = om.MFn.kAnimCurve
kConstraint = om.MFn.kConstraint
kIkHandle = om.MFn.kIkHandle
kGeometryFilter = om.MFn.kGeometryFilt
kPolyModifier = om.MFn.kMidModifier
