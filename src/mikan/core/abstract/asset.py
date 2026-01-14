# coding: utf-8

"""Abstract Asset Module.

This module provides the base Asset class for managing rig components in the Mikan framework.
It serves as a bridge between DCC application nodes (Maya, Tangerine, etc.) and Mikan's
rigging system, enabling cross-platform rig development.

The module supports:
    - Node wrapping and abstraction across different DCC applications
    - Consistent comparison and hashing for collection management
    - Type identification for asset categorization

Classes:
    Asset: Base class for wrapping DCC nodes as rig components.

Examples:
    Creating and comparing assets (Maya implementation):
        >>> from mikan.maya.core.asset import Asset
        >>> asset1 = Asset(node='joint1')
        >>> asset2 = Asset(node='joint1')
        >>> asset1 == asset2
        True

    Using assets in collections:
        >>> assets = {asset1, asset2}
        >>> len(assets)
        1
"""

__all__ = ['Asset']

from mikan.core.logger import create_logger

log = create_logger()


class Asset(object):
    """Base class for wrapping DCC nodes as rig components.

    This class provides a consistent interface for managing rig elements across
    different DCC applications. It wraps native nodes (Maya joints, transforms, etc.)
    and provides common operations like comparison, hashing, and identification.

    Subclasses should implement software-specific functionality while maintaining
    the abstract interface defined here.

    Attributes:
        type_name (str): Identifier for the asset type, defaults to 'asset'.
        node: The DCC node (joint, transform, etc.) represented by this asset.
            Must be defined by software-specific subclasses (e.g., maya.core.asset.Asset).

    Examples:
        Subclassing for Maya implementation:
            >>> class MayaAsset(Asset):
            ...     def __init__(self, node):
            ...         self.node = node

        Comparing assets:
            >>> asset1 = MayaAsset(node='joint1')
            >>> asset2 = MayaAsset(node='joint1')
            >>> asset1 == asset2
            True

    Note:
        This is an abstract base class. Use software-specific implementations
        like mikan.maya.core.asset.Asset for actual rig development.
    """

    type_name = 'asset'

    def __str__(self):
        """Return string representation of the asset.

        Returns:
            str: String representation of the underlying node.

        Examples:
            >>> asset = Asset()
            >>> asset.node = 'joint1'
            >>> str(asset)
            'joint1'
        """
        return str(self.node)

    def __repr__(self):
        """Return detailed string representation for debugging.

        Returns:
            str: Representation in format "Asset('<node_name>')".

        Examples:
            >>> asset = Asset()
            >>> asset.node = 'joint1'
            >>> repr(asset)
            "Asset('joint1')"
        """
        return 'Asset(\'{}\')'.format(self.node)

    def __eq__(self, other):
        """Check equality between two assets.

        Two assets are considered equal if they wrap the same underlying node.

        Args:
            other: Object to compare with this asset.

        Returns:
            bool: True if both assets wrap the same node, False otherwise.

        Examples:
            >>> asset1 = Asset()
            >>> asset1.node = 'joint1'
            >>> asset2 = Asset()
            >>> asset2.node = 'joint1'
            >>> asset1 == asset2
            True
            >>> asset3 = Asset()
            >>> asset3.node = 'joint2'
            >>> asset1 == asset3
            False
        """
        if isinstance(other, Asset):
            return self.node == other.node
        return False

    def __ne__(self, other):
        """Check inequality between two assets.

        Args:
            other: Object to compare with this asset.

        Returns:
            bool: True if assets are not equal, False otherwise.

        Examples:
            >>> asset1 = Asset()
            >>> asset1.node = 'joint1'
            >>> asset2 = Asset()
            >>> asset2.node = 'joint2'
            >>> asset1 != asset2
            True
        """
        return not self.__eq__(other)

    def __hash__(self):
        """Generate hash value for the asset.

        Enables assets to be used in sets and as dictionary keys.
        The hash combines the node hash with the Asset class hash.

        Returns:
            int: Hash value for this asset instance.

        Examples:
            >>> asset = Asset()
            >>> asset.node = 'joint1'
            >>> asset_set = {asset}
            >>> asset in asset_set
            True

            >>> asset_dict = {asset: 'data'}
            >>> asset_dict[asset]
            'data'
        """
        return hash(self.node) ^ hash(Asset)
