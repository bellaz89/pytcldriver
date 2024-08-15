# MIT License
#
# Copyright (c) 2024 Andrea Bellandi
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import math
from .utils import *
from collections.abc import MutableSequence, MutableMapping
from collections import UserString


class ReturnStringWrapper(str):
    @property
    def list(self):
        return ReturnListWrapper(to_list(self))

    @property
    def dict(self):
        return ReturnDictionaryWrapper(to_dict(self))

    @property
    def num(self):
        return parse_num(self)


class ReturnListWrapper(list):
    def __getitem__(self, index):
        value = super(ReturnListWrapper, self).__getitem__(index)
        return ReturnStringWrapper(value)

    def __setitem__(self, index, value):
        super(ReturnListWrapper, super).__setitem__(index, stringify(value))


class ReturnDictionaryWrapper(dict):
    def __getitem__(self, key):
        value = super(ReturnDictionaryWrapper, self).__getitem__(index)
        return ReturnStringWrapper(value)

    def __setitem__(self, key, value):
        super(ReturnDictionaryWrapper, super).__setitem__(index, stringify(value))


class Addressable(object):
    def __init__(self, interpreter, address):
        self.__dict__["__private_interpreter"] = interpreter
        self.__dict__["__private_address"] = address


def _children_addresses(ns):
    address = ns.__dict__["__private_address"]
    interpreter = ns.__dict__["__private_interpreter"]
    return namespace_children(interpreter, address)

def _function_addresses(ns):
    address = ns.__dict__["__private_address"]
    interpreter = ns.__dict__["__private_interpreter"]
    return info_commands(interpreter, address + "::*")

def _variable_addresses(ns):
    address = ns.__dict__["__private_address"]
    interpreter = ns.__dict__["__private_interpreter"]
    return info_vars(interpreter, address + "::*")

def _del_nothrow(ns, name):
    try:
        del ns[name]
    except NameError:
        pass

class NamespaceWrapper(Addressable):
    def __init__(self, interpreter, address = ""):
        super(NamespaceWrapper, self).__init__(interpreter, address)

    def __private(self):
        return (self.__dict__["__private_interpreter"],
                self.__dict__["__private_address"])

    def __call__(self, arg, *args):
        (interpreter, address) = self.__private()
        return ReturnStringWrapper(namespace_eval(interpreter, address, arg, *args))

    def __dir__(self):
        (interpreter, _) = self.__private()
        addresses = (_children_addresses(self) +
                     _function_addresses(self) +
                     _variable_addresses(self))

        return [tail(address) for address in addresses]

    def __getitem__(self, name):
        (interpreter, ns_address) = self.__private()
        address = ns_address + "::" + stringify(name)

        if namespace_exists(interpreter, address):
            return NamespaceWrapper(interpreter, address)

        elif function_exists(interpreter, address):
            return FunctionWrapper(interpreter, address)

        elif array_exists(interpreter, address):
            return ArrayWrapper(interpreter, address)

        elif variable_exists(interpreter, address):
            return StringWrapper(interpreter, address)

        else:
            raise NameError(("name '{}' is not defined " +
                             "in Tcl namespace {}").format(name,
                                                           ns_address))

    def __setitem__(self, name, value):
        (interpreter, ns_address) = self.__private()
        name = stringify(name)
        address = ns_address + "::" + stringify(name)
        interpreter = interpreter

        from pytcldriver import Namespace, Array
        if isinstance(value, Namespace):
            _del_nothrow(self, name)
            namespace_create(interpreter, address)
            ns = self[name]
            for key, val in value.items():
                ns[key] = value[key]

        if isinstance(value, NamespaceWrapper):
            _del_nothrow(self, name)
            namespace_create(interpreter, address)
            ns = self[name]
            for key in dir(value):
                ns[key] = value[key]

        elif isinstance(value, (VariableWrapper, ArrayWrapper)):
            value = value.get()
            _del_nothrow(self, name)
            interpreter.set(address, value)

        elif isinstance(value, Array):
            _del_nothrow(self, name)
            array_create(interpreter, address, value)
            arr = self[name]
            for key, val in value.items():
                arr[key] = val

        elif callable(value):
            _del_nothrow(self, name)
            interpreter.register_fun(address, value)

        else:
            _del_nothrow(self, name)
            interpreter.set(address, value)


    def __delitem__(self, name):
        (interpreter, ns_address) = self.__private()
        address = ns_address + "::" + stringify(name)
        interpreter = self.interpreter

        if namespace_exists(interpreter, address):
            namespace_delete(interpreter, address)

        elif function_exists(interpreter, address):
            function_delete(interpreter, address)
            if address in interpreter.registered_fun:
                del interpreter.registered_fun[address]

        elif array_exists(interpreter, address):
            interpreter.unset(address)

        elif variable_exists(interpreter, address):
            interpreter.unset(address)

        else:
            raise NameError(("name '{}' is not defined " +
                             "in Tcl namespace '{}'").format(name,
                                                             ns_address))

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]

    def __call__(self, command):
        pass


def parent(ns):
    (interpreter, address) = self.__private()
    return qualifiers(address)

def children(ns):
    (interpreter, address) = self.__private()
    return [NamespaceWrapper(interpreter, address) for child in _children_addresses(ns)]

def functions(ns):
    (interpreter, address) = self.__private()
    return [FunctionWrapper(interpreter, address) for fun in _function_addresses(ns)]

def variables(ns):
    (interpreter, address) = self.__private()
    vars = []
    for var in _variable_addresses(ns):
        if array_exists(interpreter, address):
            vars.append(ArrayWrapper(interpreter, address))
        else:
            vars.append(StringWrapper(interpreter, address))

    return vars


class PublicProperties(Addressable):
    def __init__(self, interpreter, address = ""):
        super(PublicProperties, self).__init__(interpreter, address)

    @property
    def interpreter(self):
        return self.__dict__["__private_interpreter"]

    @property
    def address(self):
        return self.__dict__["__private_address"]

    @property
    def name(self):
        return tail(self.address)

    @property
    def namespace(self):
        from pytcldriver import Namespace
        return Namespace(self.interpreter,
                         qualifiers(self.address))



class FunctionWrapper(PublicProperties):
    def __init__(self, interpreter, address = ""):
        super(FunctionWrapper, self).__init__(interpreter, address)

    def __call__(self, *args):
        return ReturnStringWrapper(self.interpreter.eval(self.address + " " +
                                                         join(args)))


def _get_val(val):
    if isinstance(val, VariableWrapper):
        return val.get()
    else:
        return val


class VariableWrapper(PublicProperties):
    def __init__(self, interpreter, address, rw_functions=None):
        super(VariableWrapper, self).__init__(interpreter, address)
        if rw_functions:
            self.rw_functions = rw_functions
        else:
            self.rw_functions = ("set " + stringify(address),
                                 "set " + stringify(address) + " {}")

        self.get()

    def __str__(self):
        return str(self.get())

    def __repr__(self):
        return repr(self.get())

    @property
    def dict(self):
        return DictionaryWrapper(self.interpreter, self.address, self.rw_functions)

    @dict.setter
    def dict(self, value):
        self.set(dict(value))

    @property
    def list(self):
        return ListWrapper(self.interpreter, self.address, self.rw_functions)

    @list.setter
    def list(self, value):
        self.set(list(value))

    @property
    def str(self):
        return StringWrapper(self.interpreter, self.address, self.rw_functions)

    @str.setter
    def str(self, value):
        self.set(str(value))

    @property
    def num(self):
        return NumericWrapper(self.interpreter, self.address, self.rw_functions)

    @num.setter
    def num(self, value):
        self.set(parse_num(str(value)))

    @property
    def int(self):
        return int(parse_num(self.get()))

    @int.setter
    def int(self, value):
        self.set(int(value))

    @property
    def float(self):
        return float(parse_num(self.get()))

    @float.setter
    def float(self, value):
        self.set(float(value))

    @property
    def bool(self):
        return bool(parse_num(self.get()))

    @bool.setter
    def bool(self, value):
        self.set(int(bool(value)))

    @property
    def complex(self):
        return complex(parse_num(self.get()))

    @complex.setter
    def complex(self, value):
        self.set(complex(value))

    def __setattr__(self, name, value):
        if (isinstance(value, VariableWrapper) and
            name in ["num", "str", "list", "dict"]):
            self.set(value.get())
        else:
            super(VariableWrapper, self).__setattr__(name, value)

    def __bool__(self):
        return self.bool

    def __int__(self):
        return self.int

    def __float__(self):
        return self.float

    def __complex__(self):
        return self.complex

    def _get(self):
        return self.interpreter._eval(self.rw_functions[0])

    def _set(self, value):
        return self.interpreter.eval(self.rw_functions[1].format(stringify(value)))

    def get(self):
        return self._get()

    def set(self, value):
        self._set(value)


class StringWrapper(UserString, VariableWrapper):
    def __new__(cls, p1, p2=None, p3=None):
        if p2 == None:
            return str(p1)
        else:
            return super().__new__(cls)

    def __init__(self, interpreter, address, rw_functions=None):
        self.wrapper = VariableWrapper(interpreter, address, rw_functions)

    @property
    def data(self):
        return self.get()

    @data.setter
    def data(self, value):
        self.set(value)

    @property
    def interpreter(self):
        return self.wrapper.interpreter

    @property
    def address(self):
        return self.wrapper.address

    @property
    def rw_functions(self):
        return self.wrapper.rw_functions

    def _set(self, value):
        self.wrapper._set(value)

    def _get(self):
        return self.wrapper._get()


class ListWrapper(VariableWrapper, MutableSequence):
    def _extend_rw(self, indices):
        if isinstance(indices, int):
            indices = [indices]

        indices = [normalize_list_index(index) for
                    index in
                    indices]

        (r_fun, w_fun) = self.rw_functions
        for index in indices:
            w_fun = w_fun.format("[lreplace [{}] {} {} {{}}]".format(r_fun,
                                                                     index,
                                                                     index))
            r_fun = "lindex [{}] {}".format(r_fun, index)

        return (r_fun, w_fun)

    def __getitem__(self, index):
        return StringWrapper(self.interpreter,
                                self.address,
                                self._extend_rw(index))

    def __setitem__(self, index, value):
        (_, w_fun) = self._extend_rw(index)
        self.interpreter.eval(w_fun.format(stringify(value)))

    def __delitem__(self, index):
        (r_fun, w_fun) = self.rw_functions
        if isinstance(index, tuple):
            (r_fun, w_fun) = self._extend_rw(index[:-1])
            index = index[-1]

        fun = w_fun.format("[lreplace [{}] {} {}]".format(r_fun, index, index))
        self.interpreter.eval(fun)

    def insert(self, index, value):
        (r_fun, w_fun) = self.rw_functions
        index = normalize_list_index(index)
        fun = w_fun.format("[linsert [{}] {} {}]".format(r_fun, index, value))
        self.interpreter.eval(fun)

    def __len__(self):
        return len(self.get())

    def __iter__(self):
        return iter(self.get())

    def get(self):
        return to_list(self._get())

    def set(self, value):
        self._set(list(value))


class DictionaryWrapper(VariableWrapper, MutableMapping):
    def _extend_rw(self, indices):
        if not isinstance(indices, tuple):
            indices = [indices]

        (r_fun, w_fun) = self.rw_functions
        for index in indices:
            w_fun = w_fun.format("[dict replace [{}] {} {{}}]".format(r_fun,
                                                                     index))
            r_fun = "dict get [{}] {}".format(r_fun, index)

        return (r_fun, w_fun)


    def __getitem__(self, index):
        return StringWrapper(self.interpreter,
                                self.address,
                                self._extend_rw(index))

    def __setitem__(self, index, value):
        (_, w_fun) = self._extend_rw(index)
        self.interpreter.eval(w_fun.format(stringify(value)))

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
        return to_dict(self._get())

    def set(self, value):
        self._set(dict(value))


class ArrayWrapper(PublicProperties, MutableMapping):
    def __str__(self):
        return str(self.get())

    def __repr__(self):
        return repr(self.get())

    def __getitem__(self, index):
        return StringWrapper(self.interpreter, "{}({})".format(self.address,
                                                                index))

    def __setitem__(self, index, value):
        array_set(self.interpreter, self.address, index, value)

    def __delitem__(self, index):
        array_unset(self.interpreter, self.address, index)

    def __len__(self):
        return len(self.get())

    def __iter__(self):
        return iter(self.get())

    def get(self):
        return to_dict(self.array_to_dict(self.address))

    def set(self, value):
        if variable_exists(self.interpreter, self.address):
            self.interpreter.unset(self.address)

        array_create(self.interpreter, self.address, dict(value))


class NumericWrapper(VariableWrapper):
    def _get_num(self, value):
        if isinstance(value, VariableWrapper):
            return parse_num(value._get())
        else:
            return value

    def get(self):
        return parse_num(self._get())

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
        return self

    def __isub__(self, other):
        self.set(self - other)
        return self

    def __imul__(self, other):
        self.set(self * other)
        return self

    def __itruediv__(self, other):
        self.set(self / other)
        return self

    def __ifloordiv__(self, other):
        self.set(self // other)
        return self

    def __imod__(self, other):
        self.set(self % other)
        return self

    def __ipow__(self, other, modulo=None):
        self.set(self ** other)
        return self

    def __ilshift__(self, other):
        self.set(self << other)
        return self

    def __irshift__(self, other):
        self.set(self >> other)
        return self

    def __iand__(self, other):
        self.set(self and other)
        return self

    def __ixor__(self, other):
        self.set(self ^ other)
        return self

    def __ior__(self, other):
        self.set(self or other)
        return self

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

