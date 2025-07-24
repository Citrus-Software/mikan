# coding: utf-8

import re
from collections import OrderedDict

__all__ = [
    'file_to_str_lines', 'file_to_matchs_str_lines', 'file_to_def_line',
    'file_to_def_str_line', 'file_to_def_doc', 'file_to_def_code',
    'str_extract_def_call', 'str_extract_def_name', 'str_extract_class_name',
    'str_extract_def_call_args', 'str_extract_def_args', 'str_extract_def_class_call',
]


def file_to_str_lines(file_path):
    lines = []
    with open(file_path) as fp:
        line = fp.readline()
        while line:
            line = fp.readline()
            lines.append(line)
    return lines


def file_to_matchs_str_lines(file_path, to_matchs, match_all=False):
    lines = file_to_str_lines(file_path)
    lines_match = []
    lines_nbr_match = []
    for i in range(0, len(lines)):
        if match_all:

            save_line = 1
            for to_match in to_matchs:
                if to_match not in lines[i]:
                    save_line = 0
                    break

            if save_line:
                lines_match.append(lines[i])
                lines_nbr_match.append(i)

        else:
            for to_match in to_matchs:
                if to_match in lines[i]:
                    lines_match.append(lines[i])
                    lines_nbr_match.append(i)
                    break

    return lines_match, lines_nbr_match


def file_to_function_names(file_path):
    lines = file_to_str_lines(file_path)

    re_function_name = re.compile(r'def (.*)\(.*\):')

    function_names = []
    for line in lines:
        if re_function_name.match(line):
            function_names.append(re_function_name.findall(line)[0])

    return function_names


def file_to_def_line(file_path, def_name=''):
    lines_match, line = file_to_matchs_str_lines(file_path, [def_name + '(', 'def ', ':'], match_all=True)
    if not line:
        return ''
    else:
        return line[0]


def file_to_def_str_line(file_path, def_name):
    lines_match, line = file_to_matchs_str_lines(file_path, [def_name + '(', 'def ', ':'], match_all=True)
    if not lines_match:
        return ''
    else:
        return lines_match[0]


def file_to_def_doc(file_path, def_name):
    doc_search = 0
    is_doc = 0
    lines = []
    with open(file_path) as fp:
        line = fp.readline()
        cnt = 1
        while line:
            line = fp.readline()
            cnt += 1
            if def_name in line and 'def ' in line and ':' in line:
                doc_search = 1

            if doc_search and "'''" in line:
                if is_doc:
                    is_doc = 0
                    doc_search = 0
                else:
                    is_doc = 1

            if is_doc:
                lines.append(line)

    doc = ''.join(lines[1:])

    return doc


def file_to_def_code(file_path, def_name):
    c_tabs = '\t'
    s_tabs = '    '
    c_tabs_count = 0
    s_tabs_count = 0

    def_found = 0
    is_doc = 0
    lines = []
    with open(file_path) as fp:
        line = fp.readline()

        while line:

            line = fp.readline()

            skip = 1
            for char in line:
                if char not in ['\n', '\r', '\t']:
                    skip = 0
                    break
            if skip:
                continue

            if def_name + '(' in line and 'def ' in line and ':' in line:
                def_found = 1

                c_tabs_count = 0
                s_tabs_count = 0

                for iC in range(0, len(line)):
                    if line[iC] == c_tabs:
                        c_tabs_count += 1
                    else:
                        break

                for iC in range(0, len(line), len(s_tabs)):
                    if line[iC:iC + len(s_tabs)] == s_tabs:
                        s_tabs_count += 1
                    else:
                        break

                continue

            if def_found:
                c_tabs_current_def_core = c_tabs * (c_tabs_count + 1)
                s_tabs_current_def_core = s_tabs * (s_tabs_count + 1)

                if line[0:len(c_tabs_current_def_core)] == c_tabs_current_def_core or line[0:len(s_tabs_current_def_core)] == s_tabs_current_def_core:

                    if "'''" in line:
                        is_doc = 1 - is_doc

                    if not is_doc:
                        lines.append(line)

                else:
                    def_found = 0

    return lines


def str_extract_def_call(s):
    rp = re.compile(r'def\W\w*[(].*[)]:')
    match_objs = rp.findall(s)

    return match_objs


def str_extract_def_name(s):
    rp = re.compile(r'def\W(\w*)[(]')
    match_obj = rp.search(s)

    if not match_obj:
        return ""
    else:
        return match_obj.group(1)


def str_extract_class_name(s):
    rp = re.compile(r'class\W(\w*)[(]')
    match_obj = rp.search(s)

    if not match_obj:
        return ""
    else:
        return match_obj.group(1)


def str_extract_def_call_args(s):
    rp = re.compile(r'\(\s*(.*)\s*\):')
    match_obj = rp.search(s)
    if not match_obj:
        return []
    args_str = match_obj.group(1)

    rp = re.compile(r"(.*)[\W*]$")
    match_obj = rp.search(args_str)
    if match_obj:
        args_str = match_obj.group(1)

    rp = re.compile(r" *, *")
    args_list = rp.split(args_str)

    unfinished_list = False
    args_list_fix = []
    list_to_combine = ''
    for i in range(0, len(args_list)):
        if '[' in args_list[i] and not ']' in args_list[i]:
            unfinished_list = True

        if unfinished_list:
            if not list_to_combine:
                list_to_combine += args_list[i]
            else:
                list_to_combine += ',' + args_list[i]
        else:
            args_list_fix.append(args_list[i])

        if unfinished_list and ']' in args_list[i]:
            unfinished_list = False
            args_list_fix.append(list_to_combine)
            list_to_combine = ''

    return args_list_fix


def def_code_to_kwarg(def_code, packing_kwarg):
    out_args = []

    rp = re.compile(r'\s*[\'\"]([^\"\']*)[\'\"]\s*,(.*)[)]')

    for line in def_code:
        if line.strip().startswith('#'):
            continue

        to_match_split = '{}.get('.format(packing_kwarg)

        if to_match_split in line:

            split_tmp = line.split(to_match_split)[1]

            match_obj = rp.search(split_tmp)
            if not match_obj: continue

            karg = match_obj.group(1)
            value = match_obj.group(2).strip()

            out_args.append("{} = {}".format(karg, value))

    return out_args


def def_code_to_kwarg_doc(def_code, packing_kwarg):
    out_args_doc = OrderedDict()

    match_args = r"\W*['\"]([^'\"]*)['\"]\W*,(.*)[)]"
    rp = re.compile(match_args)

    karg = None
    is_inside_doc = False
    for line in def_code:
        # Ignore completely commented lines
        if line.strip().startswith('#'):
            continue

        # Only parse part before '#' if present
        line_code = line.split('#')[0] if '#' in line else line

        to_match_split = '{}.get('.format(packing_kwarg)

        if to_match_split in line_code:
            split_tmp = line_code.split(to_match_split)[1]
            match_obj = rp.search(split_tmp)
            if not match_obj:
                continue

            karg = match_obj.group(1)
            out_args_doc[karg] = ''

            # Now try to extract doc from comment if it exists
            if '#' in line:
                line_clean = line.split('#')[1].strip()
                line_clean = line_clean.replace('\\n', '\n')
                out_args_doc[karg] = line_clean

        else:
            # Handle multiline docstrings
            if out_args_doc and '"""' in line:
                is_inside_doc = not is_inside_doc

            if is_inside_doc and '"""' not in line:
                if karg and karg in out_args_doc:
                    if out_args_doc[karg]:
                        out_args_doc[karg] += '\n'
                    out_args_doc[karg] += line.strip()

    return out_args_doc


def str_extract_def_args(path, def_name):
    def_call = file_to_def_str_line(path, def_name)
    def_call_args = str_extract_def_call_args(def_call)

    def_args = []

    packing_karg = None
    for arg in def_call_args:
        if '**' in arg:
            packing_karg = arg[2:]
        else:
            def_args.append(arg)

    def_code_kargs = []
    def_code_kargs_doc = {}
    if packing_karg is not None:
        def_code = file_to_def_code(path, def_name)
        def_code_kargs = def_code_to_kwarg(def_code, packing_karg)
        def_code_kargs_doc = def_code_to_kwarg_doc(def_code, packing_karg)

    def_args += def_code_kargs

    rp = re.compile(" *= *")
    pos_args = []
    key_args = OrderedDict()

    for arg in def_args:
        if "=" in arg:
            args_list = rp.split(arg)
            key_args[args_list[0]] = args_list[1]
        else:
            pos_args.append(arg)

    return pos_args, key_args, def_code_kargs_doc


def str_extract_def_class_call(path, def_name):
    def_lines_match, def_lines = file_to_matchs_str_lines(path, [def_name + '(', 'def ', ':'], match_all=True)
    classes_lines_match, classes_lines = file_to_matchs_str_lines(path, ['(', 'class ', '):'], match_all=True)

    if not def_lines_match or not classes_lines_match:
        return ''

    target_line = def_lines[0]

    indexes = []
    deltas = []
    delta_min = 99999999999999999999999.0
    for i in range(0, len(classes_lines)):
        delta_line = target_line - classes_lines[i]

        if 0 < delta_line:
            indexes.append(i)
            deltas.append(delta_line)
            delta_min = min(delta_min, delta_line)

    i_class = indexes[deltas.index(delta_min)]

    class_str = classes_lines_match[i_class]
    def_str = def_lines_match[0]

    # CHECK TABS
    c_tabs = '\t'
    s_tabs = '    '

    class_c_tabs_count = 0
    class_s_tabs_count = 0

    for iC in range(0, len(class_str)):
        if class_str[iC] == c_tabs:
            class_c_tabs_count += 1
        else:
            break

    for iC in range(0, len(class_str), len(s_tabs)):
        if class_str[iC:iC + len(s_tabs)] == s_tabs:
            class_s_tabs_count += 1
        else:
            break

    def_c_tabs_count = 0
    def_s_tabs_count = 0

    for iC in range(0, len(def_str)):
        if def_str[iC] == c_tabs:
            def_c_tabs_count += 1
        else:
            break

    for iC in range(0, len(def_str), len(s_tabs)):
        if def_str[iC:iC + len(s_tabs)] == s_tabs:
            def_s_tabs_count += 1
        else:
            break

    if class_c_tabs_count + 1 == def_c_tabs_count or class_s_tabs_count + 1 == def_s_tabs_count:
        return class_str

    return ''
