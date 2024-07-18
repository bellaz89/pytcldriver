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
        self.source("dict.tcl")

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
                    args = [self.lindex(args, i) for i in range(self.llength(args))]
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

    def array_get(self, name):
        return {k : self.array_key(name, k) for k in self.array_names(name)}

    def array_names(self, name):
        names = self._eval("array names " + _stringify(name))
        return [self.lindex(names, idx) for idx in range(self.llength(names))]

    def array_set(self, name, value=dict()):
        name = _stringify(name)
        for k, v in value.items():
            self.array_key(name, _stringify(k), _stringify(v))

    def array_size(self, name):
        return int(self._eval("array size " + _stringify(name)))

    def array_unset(self, name, key):
        self.eval("array unset " + _stringify(name) + " " + _stringify(str(key)))

    def array_key(self, name, key, value=None):
        key = _stringify(name + "(" + _stringify(key) + ")")
        if value:
            return self.set(key, _stringify(value))
        else:
            return self.set(key)

    def close(self, channel, mode = ""):
        self.eval("close " + _stringify(channel) + " " + mode)

    def concat(self, *values):
        return self._eval("concat " + _stringify(values))

    def dict_append(self):
        pass

    def dict_create(self, values=dict()):
        kv = [_stringify(x) for xs in values.items() for x in xs]
        return self._eval("dict create " + _join(kv))

    def dict_exist(self, dictionary, key, *keys):
        keys = [_stringify(k) for k in [key] + list(keys)]
        return self._eval("dict exists " + _stringify(dictionary) + " " + _join(keys))

    def dict_filter_key(self):
        pass

    def dict_filter_value(self):
        pass

    def dict_get(self):
        pass

    def dict_info(self, dictionary):
        return self._eval("dict info " + _stringify(dictionary))

    def dict_keys(self, dictionary):
        keys = self._eval("dict keys " + _stringify(dictionary))
        return [self.lindex(keys, idx) for idx in range(self.llength(keys))]

    def dict_merge(self, *dictionaries):
        return self._eval("dict merge " + _join(list(dictionaries)))

    def dict_remove(self, dictionary, *keys):
        return self._eval("dict remove " + _stringify(dictionary) + " " + _join(keys))

    def dict_replace(self, dictionary, values=dict()):
        kv = [_stringify(x) for xs in values.items() for x in xs]
        return self._eval("dict replace " + _stringify(dictionary) + " " + _join(kv))

    def dict_set(self, name, keys, value):
        params = [keys, value]
        if isinstance(keys, (list, tuple)):
            params = list(keys) + [value]

        return self.eval("dict set " + _join(params))

    def dict_size(self, dictionary):
        return int(self._eval("dict size " + _stringify(dictionary)))

    def dict_values(self, dictionary):
        values = self._eval("dict values " + _stringify(dictionary))
        return [self.lindex(values, idx) for idx in range(self.llength(values))]

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

    def lindex(self, value, *indices):
        return self._eval("lindex " + _stringify(value) + " " + _stringify(indices))

    def linsert(self):
        pass

    def llength(self, value):
        return int(self._eval("llength " + _stringify(value)))

    def lrange(self, value, first, last):
        return self._eval("lrange " + str(first) + " " + str(last))

    def lrepeat(self):
        pass

    def lreplace(self):
        pass

    def lreverse(self):
        pass

    def namespace_children(self):
        pass

    def namespace_current(self):
        pass

    def namespace_delete(self):
        pass

    def namespace_eval(self):
        pass

    def namespace_exists(self):
        pass

    def namespace_parent(self):
        pass

    def namespace_path(self):
        pass

    def namespace_qualifiers(self):
        pass

    def namespace_tail(self):
        pass

    def parray(self):
        pass

    def puts(self):
        pass

    def pwd(self):
        pass

    def read(self):
        pass

    def regexp(self):
        pass

    def regsub(self):
        pass

    def split(self):
        pass

    def string(self):
        pass

    def subst(self):
        pass

    def set(self, name, value=None):
        if value:
            return self.eval("set", name, value)
        else:
            return self._eval("set " + name)

    def source(self, filename):
        self.eval("source " + filename)

    def unset(self, *names, nocomplain=False):
        if nocomplain:
            self.eval("unset -nocomplain -- " + _join(names))
        else:
            self.eval("unset " + _join(names))

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


