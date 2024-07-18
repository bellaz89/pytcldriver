from subprocess import Popen, PIPE
import shlex
import socket
import tkinter
import atexit

def _join(value):
    return tkinter._join(value)

def _stringify(value):
    return tkinter._stringify(value)

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
        self.process = Popen(args,
                            stderr=PIPE,
                            stdout=PIPE,
                            env=self.env)

        atexit.register(self.exit, 0)
        self.ctrl, self.address = self.socket.accept()

        self.load_packages()

    def load_packages(self):
        self.source("dict.tcl") # For older versions of TCL

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
        return _bool(self._eval("dict exists " + _stringify(dict_) + " " + _join(keys)))

    def dict_get(self, dict_, *keys):
        return self._eval("dict get " + _stringify(dict_) + " " + _join(keys))

    def dict_set(self, dict_, key, value):
        self._eval("dict replace " + _stringify(dict_) + " " +
                                    _stringify(key) + " " +
                                    _stringify(value))

    def dict_keys(self, dict_):
        return list(self.dict_iter_keys(dict_))

    def dict_size(self, dict_):
        return int(self._eval("dict size " + _stringify(dict_)))

    def dict_values(self, dict_):
        return list(self.dict_iter_values(dict_))

    def dict_iter(self, dict_):
        return self.dict_iter_keys(dict_)

    def dict_iter_values(self, dict_):
        values = self._eval("dict values " + _stringify(dict_))
        for i in range(self.list_size(values)):
            yield self.list_get(values, i)

    def dict_iter_items(self, dict_):
        for key in self.dict_iter_keys(dict_):
            yield key, self.dict_get(dict_, key)

    def dict_iter_keys(self, dict_):
        keys = self._eval("dict keys " + _stringify(dict_))
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

    def info_tclversion(self):
        return self.eval("info tclversion")

    @property
    def version(self):
        return self.info_tclversion()

    def list_get(self, list_, *indices):
        return self._eval("lindex " + _stringify(list_) + " " + _stringify(indices))

    def list_set(self, list_, index, value):
        return self._eval("lreplace " + _stringify(_list) + " " +
                                        _stringify(index) + " " +
                                        _stringify(index) + " " +
                                        _stringify(value))

    def list_size(self, list_):
        return int(self._eval("llength " + _stringify(list_)))

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

    def namespace_qualifiers(self, address):
        return self._eval("namespace qualifiers " + _stringify(address))

    def namespace_tail(self, address):
        return self._eval("namespace tail " + _stringify(address))

    def split_address(self, address):
        return address.split("::")

    def tail(self, address):
        return self.split_address(address)[-1]

    def qualifiers(self, address):
        return "::".join(self.split_address(address)[:-1])

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

    def get_nested(self, variable, indices):
        return self._eval(self._get_nested_command(variable, indices))

    def _set_nested_command(self, variable, indices, value, stringify=True):
        if not isinstance(indices, (tuple, list)):
            indices = [indices]
        else:
            indices = list(indices)

        if stringify:
            value = _stringify(value)

        if len(indices) == 0:
            return "set " + _stringify(variable) + " " + value
        else:
            get_cmd = self._get_nested_command(variable, indices[:-1])
            index = indices[-1]
            cmd = ''
            if isinstance(index, int):
                cmd = ("[lreplace [" + get_cmd + "] " + self.normalize_list_index(index) + " "
                                                      + self.normalize_list_index(index) + " "
                                                      + value + "]")
            else:
                cmd = ("[dict replace [" + get_cmd + "] " + _stringify(index) + " "
                                                          + value + "]")

            return self._set_nested_command(variable, indices[:-1], cmd, False)


    def set_nested(self, variable, indices, value):
        self.eval(self._set_nested_command(variable, indices, value))

    def get_stdout(self):
        return self.stdout

    def get_stderr(self):
        return self.stderr

    def is_running(self):
        return self.process is not None

    def exit(self, exit_code=0):
        atexit.unregister(self.exit)
        self.ctrl.send((self.CODE_CLOSE + str(exit_code) + "\n").encode())
        self.socket.close()
        self.process.wait()
        self._save_stdout()
        self.process = None


