# coding: utf-8

"""
expression.py — DGE expression builder utilities

Adapted from Chad Vernon's `cmt/tools/dge.py` (MIT License)
https://github.com/chadmv/cmt

Only the expression-generation logic was used and has been significantly
refactored to integrate with the Mikan rig framework.

Original author: Chad Vernon
Adaptation: Thomas Guittonneau, 2025
"""

import math

from mikan.vendor import pyparsing as pp

from mikan.core.utils import re_is_int, re_is_float
from mikan.core.logger import create_logger

log = create_logger()


class ExpressionParser(object):

    def __init__(self):
        self.kwargs = {}
        self._reverse_kwargs = {}

        self.connect = True
        self.parsed_kw = {'connected': set(), 'invalid': set(), 'unused': []}

        self.expr_stack = []
        self.assignment_stack = []
        self.expression_string = None
        self.results = None
        self.container = None
        self.created_nodes = {}

        self.operators = {
            '+': self.add,
            '-': self.subtract,
            '*': self.multiply,
            '/': self.divide,
            '^': self.pow,
            '%': self.modulo,
            '|': self.logical_or,
            '&': self.logical_and,
        }
        self.conditionals = ('==', '!=', '>', '>=', '<', '<=')

        self.rotate_orders = {'XYZ', 'YZX', 'ZXY', 'XZY', 'YXZ', 'ZYX'}

        self.fn = {
            'inverse': self.inverse,
            'pow': self.pow,
            'exp': self.exp,
            'sqrt': self.sqrt,
            'clamp': self.clamp,
            'lerp': self.lerp,
            'remap': self.remap,
            'abs': self.abs,
            'sign': self.sign,
            'min': self.min,
            'max': self.max,
            'cos': self.cos,
            'sin': self.sin,
            'tan': self.tan,
            'acos': self.acos,
            'asin': self.asin,
            'atan': self.atan,
            'noise': self.noise,
            'dnoise': self.dnoise,
            'norm': self.norm,
            'dot': self.dot,
            'cross': self.cross,
            'len': self.len,
            'distance': self.distance,
            'angle': self.angle,
            'slerp': self.slerp,
            'vector': self.vector,
            'euler': self.euler,
            'quat': self.quat,
            'matrix': self.matrix,
            'transform': self.transform,
            'int': self.int,
            'bool': self.bool,
            'switch': self.switch,
            'value': self.value,
        }

        float_literal = pp.Regex(r'[+-]?\d*\.\d+(?:[eE][+-]?\d+)?|[+-]?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?')
        var_id = pp.Word(pp.alphas, pp.alphanums + '_$')

        true = pp.CaselessKeyword('TRUE') | pp.CaselessKeyword('ON')
        false = pp.CaselessKeyword('FALSE') | pp.CaselessKeyword('OFF')
        e = pp.CaselessKeyword('E')
        pi = pp.CaselessKeyword('PI')
        xyz, yzx, zxy, xzy, yxz, zyx = map(pp.CaselessKeyword, self.rotate_orders)
        constants = true | false | e | pi | xyz | yzx | zxy | xzy | yxz | zyx

        plus_op, minus_op, mult_op, div_op, exp_op, mod_op, or_op, and_op, not_op = map(pp.Literal, '+-*/^%|&!')
        add_ops = plus_op | minus_op
        mult_ops = mult_op | div_op | mod_op
        logical_ops = or_op | and_op

        l_par, r_par = map(pp.Suppress, '()')
        l_bra, r_bra = map(pp.Suppress, '[]')

        comparison_op = pp.oneOf(' '.join(self.conditionals))
        if_op = pp.Literal('?')
        else_op = pp.Literal(':')
        assignment_op = pp.Literal('=')

        # begin parser
        expr = pp.Forward()

        # add parse action that replaces the function identifier with a (name, number of args) tuple
        expr_list = pp.Group(pp.delimitedList(expr))

        fn_call = (var_id + l_par - expr_list + r_par).setParseAction(
            lambda t: t.insert(0, (t.pop(0), len(t[0])))
        )

        list_literal = (l_bra - expr_list + r_bra).setParseAction(
            lambda t: t.insert(0, ('!list', len(t[0])))
        )

        atom = (
                (fn_call | list_literal | float_literal | constants | var_id).setParseAction(self.push_first)
                | pp.Group(l_par + expr + r_par)
        )

        atom = (
                add_ops[...]
                + atom
                + (pp.Suppress('.') + pp.Word(pp.alphas)).setParseAction(self.push_component)[...]
        ).setParseAction(self.push_unary_minus)

        atom = (
                not_op[...]
                + atom
        ).setParseAction(self.push_unary_not)

        # by defining exponentiation as "atom [ ^ factor ]..." instead of "atom [ ^ atom ]...", we get right-to-left
        # exponents, instead of left-to-right that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = pp.Forward()
        factor <<= atom + (exp_op + factor).setParseAction(self.push_first)[...]

        term = factor + (mult_ops + factor).setParseAction(self.push_first)[...]
        term = term + (add_ops + term).setParseAction(self.push_first)[...]
        _expr = term + (logical_ops + term).setParseAction(self.push_first)[...]

        comparison = pp.Group(_expr) + (comparison_op + pp.Group(_expr)).setParseAction(self.push_first)[...]
        ternary = (
                comparison + (if_op + pp.Group(_expr) + else_op + pp.Group(_expr)).setParseAction(self.push_first)[...]
        )

        expr <<= ternary | _expr  # ternary recursion

        assignment = var_id + assignment_op + ~pp.FollowedBy(assignment_op)
        self.bnf = pp.Optional(assignment).setParseAction(self.push_last) + expr

    def clear(self):
        self.kwargs.clear()
        self._reverse_kwargs.clear()

        self.connect = True
        self.parsed_kw = {'connected': set(), 'invalid': set(), 'unused': []}

        del self.expr_stack[:]
        del self.assignment_stack[:]
        self.expression_string = None
        self.results = None
        self.container = None
        self.created_nodes.clear()

    def eval(self, expression_string, connect=True, **kw):
        self.clear()

        # node container?
        container = kw.get('container')
        if container:
            self.container = container

        # connect
        self.connect = connect

        # args
        self.kwargs = kw
        for k, v in kw.items():
            # Reverse variable look up to write cleaner notes
            if isinstance(v, list):
                v = tuple(v)
            self._reverse_kwargs[v] = k

        # expression
        self.expression_string = expression_string
        self.results = self.bnf.parseString(expression_string, True)
        stack = self.expr_stack[:] + self.assignment_stack[:]
        stack = self.fix_unary_stack(stack)
        result = self.evaluate_stack(stack)

        if self.connect:
            return self.optimize(result)

        # dry mode
        for k, v in kw.items():
            if k not in self.parsed_kw['invalid'] and k not in self.parsed_kw['connected']:
                self.parsed_kw['unused'].append(k)
        return self.parsed_kw

    def push_first(self, tokens):
        self.expr_stack.append(tokens[0])

    def push_last(self, tokens):
        for t in tokens:
            self.assignment_stack.append(t)

    def push_unary_minus(self, tokens):
        for i, t in enumerate(tokens):
            if t == '-':
                self.expr_stack.append('!neg')
            else:
                break

    def push_unary_not(self, tokens):
        for i, t in enumerate(tokens):
            if t == '!':
                self.expr_stack.append('!not')
            else:
                break

    def push_component(self, tokens):
        tokens[0] = ('.', tokens[0])
        self.expr_stack.append(tokens[0])

    def fix_unary_stack(self, stack):
        new_stack = []
        for s in stack:
            if s != '!neg':
                new_stack.append(s)
            else:
                v = new_stack[-1]
                if re_is_int.match(v):
                    new_stack[-1] = str(-int(v))
                elif re_is_float.match(v):
                    new_stack[-1] = str(-float(v))
                else:
                    new_stack.append(s)
        return new_stack

    def evaluate_stack(self, s):
        op, n = s.pop(), 0

        if isinstance(op, tuple):
            op, n = op

        if op == '!neg':
            op1 = self.evaluate_stack(s)
            return self.get_op_result(op, self.multiply, -1, op1)

        if op == '!not':
            op1 = self.evaluate_stack(s)
            return self.get_op_result(op, self.logical_not, op1)

        elif op == '?':
            # ternary
            if_false = self.evaluate_stack(s)
            if_true = self.evaluate_stack(s)
            condition = self.evaluate_stack(s)
            second_term = self.evaluate_stack(s)
            first_term = self.evaluate_stack(s)
            return self.get_op_result(op, self.condition, first_term, condition, second_term, if_true, if_false)

        elif op == ':':
            # return the if_true statement to the ternary
            return self.evaluate_stack(s)

        elif op in self.operators:
            # operands are pushed onto the stack in reverse order
            op2 = self.evaluate_stack(s)
            op1 = self.evaluate_stack(s)
            return self.get_op_result(op, self.operators[op], op1, op2)

        elif op in {'TRUE', 'ON'}:
            return True
        elif op in {'FALSE', 'OFF'}:
            return False
        elif op == 'PI':
            return math.pi
        elif op == 'E':
            return math.e
        elif op in self.rotate_orders:
            return self.rotate_order(op)

        elif op == '!list':
            args = list(reversed([self.evaluate_stack(s) for _ in range(n)]))
            return self.get_op_result(op, self.list, *args)

        elif op == '.':
            op1 = self.evaluate_stack(s)
            return self.get_op_result(op, self.get_component, op1, n)

        elif op in self.fn:
            # args are pushed onto the stack in reverse order
            args = list(reversed([self.evaluate_stack(s) for _ in range(n)]))
            return self.get_op_result(op, self.fn[op], *args)

        elif op[0].isalpha():
            value = self.kwargs.get(op)
            if value is None:
                if self.connect:
                    raise Exception('invalid identifier "{}"'.format(op))
                else:
                    self.parsed_kw['invalid'].add(op)
            else:
                self.parsed_kw['connected'].add(op)
            return value

        elif op in self.conditionals:
            return op

        elif op == '=':
            destination = self.evaluate_stack(s)
            source = self.evaluate_stack(s)
            if self.connect:
                self.equal(source, destination)

        elif re_is_int.match(op):
            return int(op)

        elif re_is_float.match(op):
            return float(op)

        else:
            raise Exception('invalid operator: {}'.format(op))

    def get_op_result(self, op, func, *args):
        op_str = self.op_str(op, *args)
        result = self.created_nodes.get(op_str)
        if result is None and self.connect:
            result = func(*args)
            self.created_nodes[op_str] = result
        return result

    def args_str(self, *args):
        return [str(v) for v in args]

    def op_str(self, op, *args):
        """Get the string form of the op and args.

        This is used for notes on the node as well as identifying which nodes can be
        reused.

        :param op: Name of the op
        :param args: Optional op arguments
        :return: The unique op string
        """
        args = self.args_str(*args)
        if op in self.fn:
            return '{}({})'.format(op, ', '.join(args))
        elif op == '!list':
            return '[{}]'.format(', '.join(args))
        elif op == '?':
            return '{} {} {} ? {} : {}'.format(*args)
        elif op == '!neg':
            return '-({})'.format(args[1])
        elif args:
            _args = [x if not isinstance(x, list) else tuple(x) for x in args]
            return op.join([self._reverse_kwargs.get(x, x) for x in _args])
        return op

    def equal(self, src, dst):
        pass

    def add(self, a, b):
        pass

    def subtract(self, a, b):
        pass

    def multiply(self, a, b):
        pass

    def divide(self, a, b):
        pass

    def pow(self, a, b):
        pass

    def modulo(self, a, b):
        return self.subtract(a, self.multiply(b, self.int(self.divide(a, b))))

    def inverse(self, v):
        return self.pow(v, -1)

    def exp(self, x):
        return self.pow(math.e, x)

    def sqrt(self, x):
        return self.pow(x, 0.5)

    def logical_or(self, a, b):
        pass

    def logical_and(self, a, b):
        pass

    def logical_xor(self, a, b):
        pass

    def logical_not(self, b):
        pass

    def clamp(self, value, min_value, max_value):
        pass

    def condition(self, first_term, operation, second_term, if_true, if_false):
        pass

    def lerp(self, a, b, t):
        pass

    def remap(self, x, min_old, max_old, min_new, max_new):
        pass

    def abs(self, x):
        return self.condition(x, '>=', 0, x, self.multiply(-1, x))

    def sign(self, x):
        s = self.condition(x, '>=', 0, 1, -1)
        return self.condition(x, '==', 0, 0, s)

    def min(self, a, b):
        return self.condition(a, '<=', b, a, b)

    def max(self, a, b):
        return self.condition(a, '>=', b, a, b)

    def cos(self, a):
        pass

    def sin(self, a):
        pass

    def tan(self, a):
        return self.divide(self.sin(a), self.cos(a))

    def acos(self, a):
        pass

    def asin(self, a):
        pass

    def atan(self, a):
        pass

    def noise(self, x):
        pass

    def dnoise(self, x):
        pass

    def get_component(self, v, i):
        pass

    def is_scalar(self, x):
        pass

    def is_scalar_plug(self, plug):
        pass

    def is_vector(self, v):
        pass

    def is_vector_plug(self, plug):
        pass

    def norm(self, v):
        pass

    def dot(self, v1, v2):
        pass

    def cross(self, v1, v2):
        pass

    def len(self, v):
        pass

    def distance(self, v1, v2):
        pass

    def angle(self, v1, v2):
        pass

    def list(self, *args):
        if len(args) in {2, 3, 4}:
            return list(args)
        else:
            raise TypeError('list: invalid list size')

    def vector(self, x, y, z):
        return [x, y, z]

    def euler(self, x, y, z, ro):
        pass

    def rotate_order(self, ro):
        pass

    def quat(self, x, y, z, w):
        pass

    def transform(self, t, r, s):
        pass

    def matrix(self, *args):
        pass

    def slerp(self, a, b, t):
        pass

    def int(self, x):
        pass

    def bool(self, x):
        pass

    def switch(self, *args):
        pass

    def value(self, v):
        return v

    def optimize(self, result):
        return result
