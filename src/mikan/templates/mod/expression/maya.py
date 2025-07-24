# coding: utf-8

from copy import deepcopy

import mikan.maya.cmdx as mx

import mikan.maya.core as mk
from mikan.maya.lib.connect import connect_expr
from mikan.core.logger import create_logger

log = create_logger()


class Mod(mk.Mod):

    def run(self):
        if 'op' not in self.data:
            raise mk.ModArgumentError('no operation defined')

        args = deepcopy(self.data)
        op = args.pop('op')

        parsed = connect_expr(op, connect=False, **args)
        invalid = parsed['invalid']

        if 'time' in invalid or 'frame' in invalid:
            f = mx.encode('time1')['outTime']
            if 'time' in invalid:
                args['time'] = f
                invalid.remove('time')
            if 'frame' in invalid:
                args['frame'] = f
                invalid.remove('frame')

        if 'flip' in invalid:
            args['flip'] = 1
            tpl = self.get_template()
            if tpl.do_flip():
                args['flip'] = -1
            invalid.remove('flip')

        if invalid:
            raise mk.ModArgumentError('operators {} are not defined'.format(invalid))

        connect_expr(op, **args)
