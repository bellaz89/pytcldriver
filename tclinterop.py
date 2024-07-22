from subprocess import Popen, PIPE
from collections import UserString
from collections.abc import MutableSequence, MutableMapping
import tkinter
from tkinter import _magic_re, _space_re
import shlex
import socket
import atexit
import math

# Needed modified _join and _stringify from tkinter
##########################################################

def _join(value):
    return ' '.join(map(_stringify, value))

def _stringify(value):
    if isinstance(value, bool):
        value = int(value)

    if isinstance(value, (list, tuple)):
        if len(value) == 1:
            value = _stringify(value[0])
            if _magic_re.search(value):
                value = '{%s}' % value
        else:
            value = '{%s}' % _join(value)
    elif isinstance(value, dict):
        value = '{%s}' % _join([x for xs in value.items() for x in xs])
    elif isinstance(value, complex):
        value = '{%s}' % _join([value.real, value.imag])
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

class Interpreter:
    MAX_MSG_SIZE=16384
    CODE_CALL="C"
    CODE_ERROR="E"
    CODE_RETURN="R"
    CODE_CLOSE="D"

    def __init__(self,
                 interpreter="tclsh comm.tcl {port}",
                 env=None):

        self.command_list = []
        self.env = env
        self.stdout = None
        self.stderr = None
        self.interpreter = interpreter
        self.process = None
        self.registered_fun = dict()
        self._tkinter = tkinter.Tcl()
        self._tkinter.call("source", "dict.tcl") # For older versions of TCL

    def open(self):
        self.stdout = None
        self.stderr = None
        self.command_list = []
        self.registered_fun = dict()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('', 0))
        self.socket.listen(1)

        self.port = self.socket.getsockname()[1]
        args = shlex.split(self.interpreter.format(port=self.port))
        self.process = Popen(args)
                            #stderr=PIPE,
                            #stdout=PIPE,
                            #env=self.env)

        atexit.register(self.exit, 0)
        self.ctrl, self.address = self.socket.accept()
        self.eval("source dict.tcl") # For older versions of TCL

        return NamespaceAccessor(self)

    def _save_stdout(self):
        self.stdout = self.process.stdout.read().decode("utf-8")
        self.stderr = self.process.stderr.read().decode("utf-8")

    def _check_alive(self):
        poll = self.process.poll()
        if poll:
            atexit.unregister(self.exit_)
            self.socket.close()
            self._save_stdout()
            self.process = None
            raise RuntimeError("The interpreter prematurely exited with code " + str(poll))

    def _eval(self, fun):
        if self.is_running() is False:
            raise RuntimeError("Call .open() before interacting with the interpreter")

        self._check_alive()
        self.ctrl.send((self.CODE_CALL + fun + "\n").encode())

        while True:
            self._check_alive()
            data = self.ctrl.recv(self.MAX_MSG_SIZE).decode("utf-8")
            code = data[0]
            body = data[1:]

            if code == self.CODE_RETURN:
                return body

            elif code == self.CODE_CLOSE:
                atexit.unregister(self.exit)
                self.process.wait()
                self._save_stdout()
                self.process = None
                raise RuntimeError("While executing .eval(\"" + fun + "\"):\n" + body)

            elif code == self.CODE_ERROR:
                raise RuntimeError("While executing .eval(\"" + fun + "\"):\n" + body)

            else:
                assert code == self.CODE_CALL
                try:
                    [fun_id, args] = body.split(" ", 1)
                    args = [self.lindex(args, i) for i in range(self.list_size(args))]
                    retval = self.registered_fun[fun_id](self, *args)
                    retval = _stringify(retval)
                except err:
                    self.ctrl.send((self.CODE_ERROR + str(err) + "\n").encode())
                else:
                    self.ctrl.send((self.CODE_RETURN + retval + "\n").encode())

    def eval(self, fun, *args):
        fun_str = (fun + " " + _join(args)).strip()
        self.command_list.append(fun_str)
        return self._eval(fun_str)

    def array_create(self, name, dictionary):
        if len(dictionary) == 0:
            self.array_set(name, "0", "0")
            self.array_unset(name, "0")
        else:
            for key, value in dictionary.items():
                self.array_set(name, _stringify(key), _stringify(value))

    def array_exists(self, name):
        return _bool(self._eval("array exists " + _stringify(name)))

    def array_keys(self, name):
        return list(self.array_iter_keys(name))

    def array_values(self, name):
        return list(self.array_iter_values(name))

    def array_set(self, name, key, value):
        return self.set(_stringify(name + "(" + _stringify(key) + ")"), _stringify(value))

    def array_get(self, name, key):
        return self.set(_stringify(name + "(" + _stringify(key) + ")"))

    def array_to_dict(self, name):
        return self._eval("array get " + _stringify(name))

    def array_size(self, name):
        return int(self._eval("array size " + _stringify(name)))

    def array_unset(self, name, key):
        self.eval("array unset " + _stringify(name) + " " + _stringify(str(key)))

    def array_iter(self, array):
        return self.array_iter_keys(array)

    def array_iter_keys(self, array):
        names = self._eval("array names " + _stringify(name))
        for i in range(self.list_size(names)):
            yield self.list_get(names, i)

    def array_iter_values(self, array):
        for key, value in self.array_iter_items(array):
            yield value

    def array_iter_items(self, array):
        for key in self.array_iter_keys(array):
            yield key, self.array_get(array, key)

    def array_iter_values(self, array):
        return self.dict_iter_values(self)

    def array(self, array):
        return self.dict(self.array_to_dict(array))

    def cd(self, path=None):
        if path:
            self.eval("cd " + _stringify(path))
        else:
            self.eval("cd")

    def dict_exist(self, dict_, key, *keys):
        keys = [_stringify(k) for k in [key] + list(keys)]
        return _bool(self._tkinter.call("dict",
                                        "exists",
                                        _stringify(dict_),
                                        "keys"))

    def dict_get(self, dict_, *keys):
        return self._tkinter.eval("dict get " + _stringify(dict_) + " " + _join(keys))

    def dict_set(self, dict_, key, value):
        self._tkinter.call("dict", "replace",
                            _stringify(dict_),
                            _stringify(key),
                            _stringify(value))

    def dict_keys(self, dict_):
        return list(self.dict_iter_keys(dict_))

    def dict_size(self, dict_):
        return int(self._tkinter.call("dict", "size", _stringify(dict_)))

    def dict_values(self, dict_):
        return list(self.dict_iter_values(dict_))

    def dict_iter(self, dict_):
        return self.dict_iter_keys(dict_)

    def dict_iter_values(self, dict_):
        values = self._tkinter.eval("dict values " + _stringify(dict_))
        for i in range(self.list_size(values)):
            yield self.list_get(values, i)

    def dict_iter_items(self, dict_):
        for key in self.dict_iter_keys(dict_):
            yield key, self.dict_get(dict_, key)

    def dict_iter_keys(self, dict_):
        keys = self._tkinter.eval("dict keys " + _stringify(dict_))
        for i in range(self.list_size(keys)):
            yield self.list_get(keys, i)

    def dict(self, dict_):
        return {k : v for k, v in self.dict_iter_items(dict_)}

    def history(self):
        history = self._eval("history")
        return [line.strip().split(" ", 1)[1] for line in history.splitlines()]

    def info_commands(self, pattern=None):
        if pattern:
            return self.eval("info commands " + pattern).split(" ")
        else:
            return self.eval("info commands").split(" ")

    def info_globals(self, pattern=None):
        if pattern:
            return self.eval("info globals " + pattern).split(" ")
        else:
            return self.eval("info globals").split(" ")

    def info_vars(self, pattern=None):
        if pattern:
            return self.eval("info vars " + pattern).split(" ")
        else:
            return self.eval("info vars").split(" ")

    def info_tclversion(self):
        return self.eval("info tclversion")

    @property
    def version(self):
        return self.info_tclversion()

    def list_get(self, list_, *indices):
        return self._tkinter.eval("lindex " + _stringify(list_) + " " + _stringify(indices))

    def list_set(self, list_, index, value):
        return self._tkinter.eval("lreplace " +
                                    _stringify(list_) + " " +
                                    _stringify(index) + " " +
                                    _stringify(index) + " " +
                                    _stringify(value))

    def list_size(self, list_):
        return self._tkinter.call("llength", _stringify(list_))

    def list_iter(self, list_):
        for i in range(self.list_size(list_)):
            yield self.list_get(list_, i)

    def list(self, value):
        return list(self.list_iter(value))

    def namespace_children(self, namespace=None):
        if namespace:
            return self.list(self._eval("namespace children " + _stringify(namespace)))
        else:
            return self.list(self._eval("namespace children"))

    def namespace_current(self):
        return self._eval("namespace current")

    def namespace_delete(self, *namespaces):
        self.eval("namespace delete " + _join(namespaces))

    def _namespace_eval(self, namespace, fun):
        return self._eval("namespace eval " + fun_str)

    def namespace_eval(self, namespace, fun, *args):
        return self.eval("namespace eval " + _join([fun] + list(args)))

    def namespace_exists(self, namespace):
        return _bool(self._eval("namespace exists " + _stringify(namespace)))

    def namespace_parent(self, namespace):
        return self._eval("namespace parent " + _stringify(namespace))

    def namespace_qualifiers(self, namespace):
        return self._eval("namespace qualifiers " + _stringify(namespace))

    def namespace_tail(self, namespace):
        return self._eval("namespace tail " + _stringify(namespace))

    def function_exists(self, address):
        return self._eval("info commands " + address) == address

    def function_delete(self, address):
        self.eval("rename", address, "\"\"")

    def variable_exists(self, address):
        return self._eval("info vars " + address) == address

    @staticmethod
    def split_address(address):
        return address.split("::")

    @staticmethod
    def tail(address):
        return Interpreter.split_address(address)[-1]

    @staticmethod
    def qualifiers(address):
        return "::".join(Interpreter.split_address(address)[:-1])

    def puts(self, *values):
        self._eval("puts " + _stringify(values))

    def pwd(self):
        return self._eval("pwd")

    def set(self, name, value=None):
        if value:
            return self.eval("set", name, value)
        else:
            return self._eval("set " + name)

    def get(self, name):
        return self.set(name)

    def source(self, filename):
        self.eval("source " + filename)

    def unset(self, *names, nocomplain=False):
        if nocomplain:
            self.eval("unset -nocomplain -- " + _join(names))
        else:
            self.eval("unset " + _join(names))

    @staticmethod
    def normalize_list_index(index):
        if index < 0:
            return "end" + str(index + 1)
        else:
            return str(index)

    def _get_nested_command(self, variable, indices):
        if not isinstance(indices, (tuple, list)):
            indices = [indices]
        else:
            indices = list(indices)

        cmd = "set " + _stringify(variable)
        for index in indices:
            if isinstance(index, int):
                cmd = "lindex [" + cmd + "] " + self.normalize_list_index(index)
            else:
                cmd = "dict get [" + cmd + "] " + _stringify(index)

        return cmd

    def parse_num(self, value):
        try:
            return self._tkinter.call("expr", value, "+", "0")
        except:
            try:
                if self.list_size(value) == 2:
                    return complex(parse_num(self.list_get(value, 0)),
                                   parse_num(self.list_get(value, 1)))
                else:
                    raise Exception("Error")
            except:
                raise TypeError("Can't convert " + value + " to a number")

    def get_stdout(self):
        return self.stdout

    def get_stderr(self):
        return self.stderr

    def is_running(self):
        return self.process is not None

    def register_fun(self, name, fun):
        self.registered_fun[name] = fun
        fun_src = f"""
        proc {name} {{args}} {{
            puts -nonewline $sock [concat $::tclinterop_private_::code_call {name} $args]
            return [::tclinterop_private::communicate]
        }}
        """
        self.eval(fun_src)

    def exit(self, exit_code=0):
        atexit.unregister(self.exit)
        self.ctrl.send((self.CODE_CLOSE + str(exit_code) + "\n").encode())
        self.socket.close()
        self.process.wait()
        self._save_stdout()
        self.process = None

    def __enter__(self):
        root = self.open()
        return self, root

    def __exit__(self, type, value, traceback):
        self.close()


class Addressable(object):
    def __init__(self, interpreter, address):
        self.__dict__["__private_interpreter"] = interpreter
        self.__dict__["__private_address"] = address

def _children_addresses(ns):
    address = ns.__dict__["__private_address"]
    interpreter = ns.__dict__["__private_interpreter"]
    return interpreter.namespace_children(address)

def _function_addresses(ns):
    address = ns.__dict__["__private_address"]
    interpreter = ns.__dict__["__private_interpreter"]
    return interpreter.info_commands(address + "::*")

def _variable_addresses(ns):
    address = ns.__dict__["__private_address"]
    interpreter = ns.__dict__["__private_interpreter"]
    return interpreter.info_vars(address + "::*")

def _del_nothrow(ns, name):
    try:
        del ns[name]
    except NameError:
        pass

class NamespaceAccessor(Addressable):
    def __init__(self, interpreter, address = ""):
        super(NamespaceAccessor, self).__init__(interpreter, address)

    def __dir__(self):
        interpreter = self.__private_interpreter
        addresses = (_children_addresses(self) +
                     _function_addresses(self) +
                     _variable_addresses(self))

        return [interpreter.tail(address) for address in addresses]

    def __getitem__(self, name):
        address = self.__private_address + "::" + _stringify(name)
        interpreter = self.__private_interpreter

        if interpreter_.namespace_exists(address):
            return NamespaceAccessor(interpreter, address)

        elif interpreter_.function_exists(address):
            return FunctionAccessor(interpreter, address)

        elif interpreter_.array_exists(address):
            return ArrayAccessor(interpreter, address)

        elif interpreter_.variable_exists(address):
            return StringAccessor(interpreter, address)

        else:
            raise NameError(("name '{}' is not defined " +
                             "in Tcl namespace {}").format(name,
                                                           self.__private_address))

    def __setitem__(self, name, value):
        name = _stringify(name)
        address = self.__private_address + "::" + _stringify(name)
        interpreter = self.__private_interpreter

        if isinstance(value, Namespace):
            _del_nothrow(self, name)
            interpreter.namespace_create(address)
            ns = self[address_]
            for key, val in value:
                ns[key] = val

        elif isinstance(value, Array):
            _del_nothrow(self, name)
            interpreter_.array_create(address, value)

        elif callable(value):
            _del_nothrow(self, name)
            interpreter.register_fun(address, value)

        elif isinstance(value, VariableAccessor):
            value = value.get()
            _del_nothrow(self, name)
            interpreter_.set(address, value)

        else:
            value = _stringify(value)
            _del_nothrow(self, name)
            interpreter_.set(address, value)


    def __delitem__(self, name):
        address = self.__private_address + "::" + _stringify(name)
        interpreter = self.__private_interpreter

        if interpreter.namespace_exists(address):
            interpreter.namespace_delete(address)

        elif interpreter.function_exists(address):
            interpreter.function_delete(address)
            if address in interpreter.registered_fun:
                del interpreter.registered_fun[address]

        elif interpreter.array_exists(address):
            interpreter.unset(address)

        elif interpreter.variable_exists(address):
            interpreter.unset(address)

        else:
            raise NameError(("name '{}' is not defined " +
                             "in Tcl namespace '{}'").format(name,
                                                             self.__private_address))

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]

    def __call__(self, command):
        pass


def parent(ns):
    address = ns.__dict__["__private_address"]
    interpreter = ns.__dict__["__private_interpreter"]
    return interpreter.qualifiers(address)

def children(ns):
    address = ns.__dict__["__private_address"]
    interpreter = ns.__dict__["__private_interpreter"]
    return [NamespaceAccessor(interpreter, address) for child in _children_addresses(ns)]

def functions(ns):
    address = ns.__dict__["__private_address"]
    interpreter = ns.__dict__["__private_interpreter"]
    return [FunctionAccessor(interpreter, address) for fun in _function_addresses(ns)]

def variables(ns):
    address = ns.__dict__["__private_address"]
    interpreter = ns.__dict__["__private_interpreter"]
    vars = []
    for var in _variable_addresses(ns):
        if interpreter.array_exists(address):
            vars.append(ArrayAccessor(interpreter, address))
        else:
            vars.append(StringAccessor(interpreter, address))

    return vars

class PublicAttributes:
    @property
    def interpreter(self):
        return interpreter(self)

    @property
    def address(self):
        return address(self)

    @property
    def name(self):
        return interpreter(self)

    @property
    def namespace(self):
        return namespace(self)

class FunctionAccessor(Addressable, PublicAttributes):
    def __call__(self, *args):
        return self.interpreter.eval(self.address() + " " + _join(args))

def _get_val(val):
    if isinstance(val, VariableAccessor):
        return val.get()
    else:
        return val


class VariableAccessor(Addressable, PublicAttributes):
    def __init__(self, interpreter, address, rw_functions=None):
        Addressable.__init__(self, interpreter, address)
        if rw_functions:
            self.rw_functions = rw_functions
        else:
            self.rw_functions = ("set " + _stringify(address),
                                 "set " + _stringify(address) + " {}")

        self.get()

    def __str__(self):
        return self.get_str()

    def __repr__(self):
        return self.get_str()

    def dict(self):
        return DictionaryAccessor(self.interpreter, self.address, self.rw_functions)

    def list(self):
        return ListAccessor(self.interpreter, self.address, self.rw_functions)

    def str(self):
        return StringAccessor(self.interpreter, self.address, self.rw_functions)

    def num(self):
        return NumericAccessor(self.interpreter, self.address, self.rw_functions)

    def _parse_num(self):
        return interpreter.parse_num(self.get())

    @property
    def int(self):
        return int(self._parse_num())

    @property
    def float(self):
        return float(self._parse_num())

    @property
    def bool(self):
        return bool(self._parse_num())

    @property
    def complex(self):
        return complex(self._parse_num())

    def __bool__(self):
        return self.bool

    def __int__(self):
        return self.int

    def __float__(self):
        return self.float

    def __complex__(self):
        return self.complex

    def _get(self):
        return interpreter._eval(self.rw_functions[0])

    def _set(self, value):
        return interpreter.eval(self.rw_functions[1].format(_stringify(value)))

    def get(self):
        return self._get()

    def set(self, value):
        self._set(value)


class StringAccessor(VariableAccessor, UserString):
    @property
    def data(self):
        return self.get()

    @data.setter
    def data(self, value):
        self.set(value)

class ListAccessor(VariableAccessor, MutableSequence):
    def _extend_rw(self, indices):
        if isinstance(indices, int):
            indices = [indices]

        indices = [self.interpreter.normalize_list_index(index) for
                    index in
                    indices]

        (r_fun, w_fun) = self.rw_functions
        for index in indices:
            w_fun = w_fun.format("[lreplace [{}] {} {}]".format(r_fun,
                                                                index,
                                                                index))
            r_fun = "lindex [{}] {}".format(r_fun, index)

        return (r_fun, w_fun)

    def __getitem__(self, index):
        return StringAccessor(self.interpreter,
                                self.address,
                                self._extend_rw(index))

    def __setitem__(self, index, value):
        (_, w_fun) = self._extend_rw(index)
        self.eval(w_fun.format(_stringify(value)))

    def __delitem__(self, index):
        (r_fun, w_fun) = self.rw_functions
        if isinstance(index, tuple):
            (r_fun, w_fun) = self._extend_rw(index[:-1])
            index = index[-1]

        fun = w_fun.format("[lremove [{}] {}]".format(r_fun, index))
        self.interpreter.eval(fun)

    def insert(self, index, value):
        (r_fun, w_fun) = self.rw_functions
        index = self.interpreter.normalize_list_index(index)
        fun = w_fun.format("[linsert [{}] {} {}]".format(r_fun, index, value))
        self.interpreter.eval(fun)

    def __len__(self):
        return len(self.get())

    def __iter__(self):
        return iter(self.get())

    def get(self):
        return self.interpreter.list(self._get())

    def set(self, value):
        self._set(list(value))

class DictionaryAccessor(VariableAccessor, MutableMapping):
    def _extend_rw(self, indices):
        if not isinstance(indices, tuple):
            indices = [indices]

        (r_fun, w_fun) = self.rw_functions

        w_fun = w_fun.format("[dict set [{}] {}]".format(r_fun,
                                                         _join(indices)))

        r_fun = "dict get [{}] {}".format(r_fun, _join(indices))
        return (r_fun, w_fun)


    def __getitem__(self, index):
        return StringAccessor(self.interpreter,
                                self.address,
                                self._extend_rw(index))

    def __setitem__(self, index, value):
        (_, w_fun) = self._extend_rw(index)
        self.eval(w_fun.format(_stringify(value)))

    def __delitem__(self, index):
        (r_fun, w_fun) = self.rw_functions
        if isinstance(index, tuple):
            (r_fun, w_fun) = self._extend_rw(index[:-1])
            index = index[-1]

        fun = w_fun.format("[dict remove [{}] {}]".format(r_fun, index))
        self.interpreter.eval(fun)

    def __len__(self):
        return len(self.get())

    def __iter__(self):
        return iter(self.get())

    def get(self):
        return self.interpreter.dict(self._get())

    def set(self, value):
        self._set(dict(value))


class ArrayAccessor(Addressable, MutableMapping):
    def __getitem__(self, index):
        return StringAccessor(self.interpreter, "{}({})".format(self.address,
                                                                index))

    def __setitem__(self, index, value):
        self.interpreter.array_set(value)

    def __delitem__(self, index):
        self.interpreter.array_unset(index)

    def __len__(self):
        return len(self.get())

    def __iter__(self):
        return iter(self.get())

    def get(self):
        return self.interpreter.dict(self.array_to_dict(self.address))

    def set(self, value):
        if self.interpreter.variable_exists(self.address):
            self.interpreter.unset(self.address)

        self.interpreter.array_create(dict(value))


class NumericAccessor(VariableAccessor):
    def _get_num(self, value):
        if isinstance(value, VariableAccessor):
            return self._parse_num(value._get())
        else:
            return value

    def get(self, value):
        return self._parse_num(self._get())

    def __add__(self, other):
        return self.get() + self._get_num(other)

    def __sub__(self, other):
        return self.get() - self._get_num(other)

    def __mul__(self, other):
        return self.get() * self._get_num(other)

    def __truediv__(self, other):
        return self.get() / self._get_num(other)

    def __floordiv__(self, other):
        return self.get() // self._get_num(other)

    def __mod__(self, other):
        return self.get() % self._get_num(other)

    def __divmod__(self, other):
        return divmod(self.get(), self._get_num(other))

    def __pow__(self, other):
        return self.get() ** self._get_num(other)

    def __lshift__(self, other):
        return self.get() << self._get_num(other)

    def __rshift__(self, other):
        return self.get() >> self._get_num(other)

    def __and__(self, other):
        return self.get() and self._get_num(other)

    def __xor__(self, other):
        return self.get() ^ self._get_num(other)

    def __or__(self, other):
        return self.get() or self._get_num(other)

    def __radd__(self, other):
        return self._get_num(other) + self.get()

    def __rsub__(self, other):
        return self._get_num(other) - self.get()

    def __rmul__(self, other):
        return self._get_num(other) * self.get()

    def __rtruediv__(self, other):
        return self._get_num(other) / self.get()

    def __rfloordiv__(self, other):
        return self._get_num(other) // self.get()

    def __rmod__(self, other):
        return self._get_num(other) % self.get()

    def __rdivmod__(self, other):
        return divmod(self._get_num(other), self.get())

    def __rpow__(self, other):
        return self._get_num(other) ** self.get()

    def __rlshift__(self, other):
        return self._get_num(other) << self.get()

    def __rrshift__(self, other):
        return self._get_num(other) >> self.get()

    def __rand__(self, other):
        return self._get_num(other) and self.get()

    def __rxor__(self, other):
        return self._get_num(other) ^ self.get()

    def __ror__(self, other):
        return self._get_num(other) or self.get()

    def __iadd__(self, other):
        self.set(self + other)

    def __isub__(self, other):
        self.set(self - other)

    def __imul__(self, other):
        self.set(self * other)

    def __itruediv__(self, other):
        self.set(self / other)

    def __ifloordiv__(self, other):
        self.set(self // other)

    def __imod__(self, other):
        self.set(self % other)

    def __ipow__(self, other, modulo=None):
        self.set(self ** other)

    def __ilshift__(self, other):
        self.set(self << other)

    def __irshift__(self, other):
        self.set(self >> other)

    def __iand__(self, other):
        self.set(self and other)

    def __ixor__(self, other):
        self.set(self ^ other)

    def __ior__(self, other):
        self.set(self or other)

    def __neg__(self):
        return -self.get()

    def __pos__(self):
        return self.get()

    def __abs__(self):
        return abs(self.get())

    def __invert__(self):
        return ~self.get()

    def __index__(self):
        value = self.get()
        if isinstance(value, int):
            return value
        else:
            raise TypeError("Value {} is not an integer".format(value))

    def __round__(self, ndigits=None):
        if ndigits:
            return round(self.get(), self._get_num(ndigits))
        else:
            return round(self.get())

    def __trunc__(self):
        return math.trunc(self.get())

    def __floor__(self):
        return math.floor(self.get())

    def __ceil__(self):
        return math.ceil(self.get())

class Namespace(dict):
    pass

class Array(dict):
    pass
