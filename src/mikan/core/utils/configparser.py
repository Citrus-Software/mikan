# coding: utf-8

from six.moves import range


class ConfigParser(object):

    def __init__(self, node, attr='notes'):
        """placeholder"""
        self.node = node
        self.attr = attr

    def __getitem__(self, key):
        return ConfigSection(self, key)

    def __setitem__(self, key, value):
        ConfigSection(self, key).write('{}'.format(value))

    def __delitem__(self, key):
        section = self[key]
        section.delete()

    def __iter__(self):
        counter = {}
        for s in self.sections():
            if s not in counter:
                counter[s] = 0
            section = ConfigSection(self, s)[counter[s]]
            counter[s] += 1
            yield section

    def __contains__(self, key):
        return key in self.sections()

    def _read(self):
        """placeholder"""
        return ''

    def _write(self, data):
        """placeholder"""
        pass

    def append(self, section):
        return ConfigSection(self, section)[self.sections().count(section)]

    def get_lines(self):
        data = self._read()
        if data:
            return data.split('\n')
        else:
            return []

    def set_lines(self, lines):
        self._write('\n'.join(lines))

    def sections(self):
        lines = self.get_lines()
        s = []
        for line in lines:
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                s.append(line[1:-1])
        return s

    def get_all(self):
        s = []
        for section in self.sections():
            s.append(ConfigSection(self, section))
        return s

    def delete_all(self):
        for s in self.sections():
            self[s].delete()

    @staticmethod
    def is_section(x):
        return isinstance(x, ConfigSection)


class ConfigSection(object):
    def __init__(self, parser, name):
        self.parser = parser
        self.name = name
        self.n = None

    def __str__(self):
        lines = self.get_lines()
        ini = '[{}]'.format(self.name)
        if lines:
            return ini + '\n'.join(lines) + '\n'
        else:
            return ini

    __repr__ = __str__

    def __getitem__(self, n):
        n = int(n)
        s = self.parser.sections().count(self.name)
        if s == 0 and n == -1:
            n = 0
        if n < 0:
            n = s + n
        if n > s or n < 0:
            raise IndexError('index {} does not exist for {}'.format(n, self.header))
        cs = ConfigSection(self.parser, self.name)
        cs.n = n
        return cs

    def __setitem__(self, key, value):
        section = self[key]
        section.write('{}'.format(value))

    def __delitem__(self, key):
        section = self[key]
        section.delete()

    def __iter__(self):
        s = self.parser.sections().count(self.name)
        if self.n is None:
            return iter([ConfigSection(self.parser, self.name)[x] for x in range(s)])
        else:
            raise TypeError('indexed section {} is not iterable'.format(self.header))

    def __eq__(self, other):
        if not isinstance(other, ConfigSection):
            return False
        if self.parser.node != other.parser.node:
            return False
        if self.name != other.name:
            return False
        if self.index != other.index:
            return False
        return True

    @property
    def header(self):
        return '[{}]'.format(self.name)

    @property
    def index(self):
        if self.n is not None:
            return self.n
        return 0

    def parse(self):
        lines = self.parser.get_lines()
        line_start = -1
        line_end = -1
        n = 0
        _n = self.index

        for i, line in enumerate(lines):
            if line_start != -1 and line_end == -1:
                if line.startswith('['):
                    line_end = i
            if line.strip() == self.header and n != -1:
                if n == _n:
                    line_start = i + 1
                    n = -1
                else:
                    n += 1
        if line_end == -1:
            line_end = None
        if line_start == -1:
            return dict(lines=[])
        return dict(lines=lines[line_start:line_end], start=line_start, end=line_end)

    def get_lines(self):
        return self.parse()['lines']

    def set_lines(self, lines):
        p = self.parse()
        old = self.parser.get_lines()

        start = p.get('start')
        end = p.get('end')

        new = []
        if start:
            for line in old[:start - 1]:
                new.append(line)
        else:
            new = old

        new.append(self.header)
        for line in lines:
            new.append(line)

        if start and end:
            for line in old[end:]:
                new.append(line)

        if end is None and new[-1]:
            new.append('')

        self.parser.set_lines(new)

    def read(self):
        lines = self.get_lines()
        if lines:
            return '\n'.join(lines)
        return ''

    def write(self, data):
        if isinstance(data, (list, tuple)):
            self.set_lines(data)
        else:
            self.set_lines(data.split('\n'))

    def delete(self):
        p = self.parse()
        old = self.parser.get_lines()

        start = p.get('start')
        end = p.get('end')

        new = []
        if start:
            for line in old[:start - 1]:
                new.append(line)

            if end:
                for line in old[end:]:
                    new.append(line)

            self.parser.set_lines(new)

    def switch(self, other):
        lines0 = self.get_lines()
        lines1 = other.get_lines()
        self.set_lines(lines1)
        other.set_lines(lines0)

        header0 = self.name
        header1 = other.name
        if header0 != header1:
            p0 = self.parse()
            p1 = other.parse()
            start0 = p0['start']
            start1 = p1['start']

            lines = self.parser.get_lines()
            lines[start0 - 1] = header1
            lines[start1 - 1] = header0
            self.parser.set_lines(lines)
