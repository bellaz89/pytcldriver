import tkinter
from tkinter import _magic_re, _space_re
from importlib_resources import files

TKINTER = tkinter.Tcl()
TKINTER.eval(files("pytcldriver.tcl").joinpath("dict.tcl").read_text()) # For older versions of TCL

# Needed modified join and stringify from tkinter
##########################################################

def join(value):
    return ' '.join(map(stringify, value))

def stringify(value):
    if isinstance(value, bool):
        value = int(value)

    if isinstance(value, (list, tuple)):
        if len(value) == 1:
            value = stringify(value[0])
            if _magic_re.search(value):
                value = '{%s}' % value
        else:
            value = '{%s}' % join(value)
    elif isinstance(value, dict):
        value = '{%s}' % join([x for xs in value.items() for x in xs])
    elif isinstance(value, complex):
        value = '{%s}' % join([value.real, value.imag])
    else:
        if isinstance(value, bytes):
            value = str(value, 'latin1')
        else:
            value = str(value)
        if not value:
            value = '{}'
        elif _magic_re.search(value):
            # add '\' before special characters and spaces
            value = _magic_re.sub(r'\\\1', value)
            value = value.replace('\n', r'\n')
            value = _space_re.sub(r'\\\1', value)
            if value[0] == '"':
                value = '\\' + value
        elif value[0] == '"' or _space_re.search(value):
            value = '{%s}' % value
    return value

##########################################################

def _bool(value):
    return bool(int(value))

def array_create(interp, name, dictionary):
    if len(dictionary) == 0:
        interp.array_set(name, "0", "0")
        interp.array_unset(name, "0")
    else:
        for key, value in dictionary.items():
            interp.array_set(name, stringify(key), stringify(value))

def array_exists(interp, name):
    return _bool(interp._eval("array exists " + stringify(name)))

def array_keys(interp, name):
    return list(array_iter_keys(interp, name))

def array_values(interp, name):
    return list(array_iter_values(interp, name))

def array_set(interp, name, key, value):
    return interp.set(stringify(name + "(" + stringify(key) + ")"),
                      stringify(value))

def array_get(interp, name, key):
    return interp.set(stringify(name + "(" + stringify(key) + ")"))

def array_to_dict(interp, name):
    return interp._eval("array get " + stringify(name))

def array_size(interp, name):
    return int(interp._eval("array size " + stringify(name)))

def array_unset(interp, name, key):
    interp.eval("array unset " + stringify(name) + " " + stringify(str(key)))

def array_iter(interp, array):
    return array_iter_keys(interp, array)

def array_iter_keys(interp, array):
    names = interp._eval("array names " + stringify(name))
    for i in range(list_size(interp, names)):
        yield list_get(interp, names, i)

def array_iter_values(interp, array):
    for key, value in array_iter_items(interp, array):
        yield value

def array_iter_items(interp, array):
    for key in interp.array_iter_keys(array):
        yield key, array_get(interp, array, key)

def array(interp, array):
    return to_dict(array_to_dict(interp, array))

def dict_exist(dict_, key, *keys):
    keys = [stringify(k) for k in [key] + list(keys)]
    return _bool(TKINTER.call("dict",
                              "exists",
                              stringify(dict_),
                              "keys"))

def dict_get(dict_, *keys):
    return TKINTER.eval("dict get " + stringify(dict_) + " " + join(keys))

def dict_set(dict_, key, value):
    TKINTER.call("dict", "replace",
                        stringify(dict_),
                        stringify(key),
                        stringify(value))

def dict_keys(dict_):
    return list(dict_iter_keys(dict_))

def dict_size(dict_):
    return int(TKINTER.call("dict", "size", stringify(dict_)))

def dict_values(dict_):
    return list(dict_iter_values(dict_))

def dict_iter(dict_):
    return dict_iter_keys(dict_)

def dict_iter_values(dict_):
    values = TKINTER.eval("dict values " + stringify(dict_))
    for i in range(list_size(values)):
        yield list_get(values, i)

def dict_iter_items(dict_):
    for key in interp.dict_iter_keys(dict_):
        yield key, dict_get(dict_, key)

def dict_iter_keys(dict_):
    keys = TKINTER.eval("dict keys " + stringify(dict_))
    for i in range(list_size(keys)):
        yield list_get(keys, i)

def to_dict(dict_):
    return {k : v for k, v in dict_iter_items(dict_)}

def history(interp):
    history = interp._eval("history")
    return [line.strip().split(" ", 1)[1] for line in history.splitlines()]

def info_commands(interp, pattern=None):
    if pattern:
        return interp.eval("info commands " + pattern).split(" ")
    else:
        return interp.eval("info commands").split(" ")

def info_globals(interp, pattern=None):
    if pattern:
        return interp.eval("info globals " + pattern).split(" ")
    else:
        return interp.eval("info globals").split(" ")

def info_vars(interp, pattern=None):
    if pattern:
        return interp.eval("info vars " + pattern).split(" ")
    else:
        return interp.eval("info vars").split(" ")

def list_get(list_, *indices):
    return TKINTER.eval("lindex " + stringify(list_) + " " +
                        stringify(indices))

def list_set(list_, index, value):
    return TKINTER.eval("lreplace " +
                        stringify(list_) + " " +
                        stringify(index) + " " +
                        stringify(index) + " " +
                        stringify(value))

def list_range(list_, start, end):
    return TKINTER.eval("lrange" + " " +
                        stringify(list_) + " " +
                        stringify(start) + " " +
                        stringify(end))

def list_size(list_):
    return TKINTER.call("llength", list_)

def list_iter(list_):
    for i in range(list_size(list_)):
        yield list_get(list_, i)

def to_list(value):
    return list(list_iter(value))

def namespace_create(interp, namespace):
    interp.eval("namespace eval {} \"puts -nonewline {{}}\"".format(namespace))

def namespace_children(interp, namespace=None):
    if namespace:
        return to_list(interp._eval("namespace children " +
                                    stringify(namespace)))
    else:
        return to_list(interp._eval("namespace children"))

def namespace_current(interp):
    return interp._eval("namespace current")

def namespace_delete(interp, *namespaces):
    interp.eval("namespace delete " + join(namespaces))

def _namespace_eval(interp, namespace, fun):
    return interp._eval("namespace eval " + fun_str)

def namespace_eval(interp, namespace, fun, *args):
    return interp.eval("namespace eval " + join([fun] + list(args)))

def namespace_exists(interp, namespace):
    return _bool(interp._eval("namespace exists " + stringify(namespace)))

def namespace_parent(interp, namespace):
    return interp._eval("namespace parent " + stringify(namespace))

def namespace_qualifiers(interp, namespace):
    return interp._eval("namespace qualifiers " + stringify(namespace))

def namespace_tail(interp, namespace):
    return interp._eval("namespace tail " + stringify(namespace))

def function_exists(interp, address):
    return interp._eval("info commands " + address) == address

def function_delete(interp, address):
    interp.eval("rename", address, "\"\"")

def variable_exists(interp, address):
    return interp._eval("info vars " + address) == address

def normalize_list_index(index):
        if index < 0:
            return "end" + str(index + 1)
        else:
            return str(index)

def parse_num(value):
        try:
            return TKINTER.call("expr", value, "+", "0")
        except:
            try:
                if list_size(value) == 2:
                    return complex(parse_num(list_get(value, 0)),
                                   parse_num(list_get(value, 1)))
                else:
                    raise Exception("Error")
            except:
                raise TypeError("Can't convert " + value + " to a number")

def split_address(address):
    return address.split("::")

def tail(address):
    return split_address(address)[-1]

def qualifiers(address):
    return "::".join(split_address(address)[:-1])


