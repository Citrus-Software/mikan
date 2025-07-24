# coding: utf-8

__all__ = ['Asset']

from mikan.core.logger import create_logger

log = create_logger()


class Asset(object):
    type_name = 'asset'

    def __str__(self):
        return str(self.node)

    def __repr__(self):
        return 'Asset(\'{}\')'.format(self.node)

    def __eq__(self, other):
        if isinstance(other, Asset):
            return self.node == other.node
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.node) ^ hash(Asset)
