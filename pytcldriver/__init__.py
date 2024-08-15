from subprocess import Popen, PIPE
import shlex
import socket
import atexit

from .communicator import Communicator
from .wrappers import NamespaceWrapper
from .utils import join, stringify, list_get, list_range, list_size

class Interpreter:
    MAX_MSG_SIZE=16384

    def __init__(self,
                 command="tclsh {script} {tcl_args}",
                 env=None,
                 redirect_stdout=True,
                 communication="auto",
                 port=None,
                 encrypt_data=True,
                 args_passing="file"):

        self.command_list = []
        self.command = command
        self.env = env
        self.redirect_stdout = redirect_stdout
        self.communication = communication
        self.encrypt_data = encrypt_data
        self.args_passing = args_passing
        self.port = port
        self.registered_fun = []

        self.communicator = Communicator(command,
                                         env,
                                         redirect_stdout,
                                         communication,
                                         port,
                                         encrypt_data,
                                         args_passing)

    def open(self):
        self.registered_fun = []
        self.communicator.open()
        return NamespaceWrapper(self)

    def _save_stdout(self):
        (self.stdout, self.stderr) = self.communicator.get_stdout()

    def _eval(self, fun):
        self.communicator.send(fun)

        while True:
            data = self.communicator.receive()
            code = list_get(data, 0)
            args = list_range(data, 1, "end")

            if code == "return":
                return args

            elif code == "exit":
                self.communicator.close()
                raise RuntimeError("The TCL interpreter has closed while " \
                                   "executing .eval(\"" + fun + "\")")

            elif code == "error":
                raise RuntimeError("While executing .eval(\"" + fun + "\"): " +
                                   args)

            elif code == "call":
                [fun_id, args] = args.split(" ", 1)
                args = [list_get(args, i)
                        for i
                        in range(list_size(args))]

                retval = None
                try:
                    retval = self.registered_fun[int(fun_id)](*args)
                    retval = stringify(retval)
                    self.communicator.send("return " + retval)
                except Exception as err:
                    self.communicator.send("error " + "\"" + str(err) + "\"")

            else:
                raise RuntimeError("Unknown code " + code)

    def eval(self, fun, *args):
        fun_str = (fun + " " + join(args)).strip()
        self.command_list.append(fun_str)
        return self._eval(fun_str)

    @property
    def version(self):
        return self._eval("info tcl_version")

    def puts(self, *values):
        self._eval("puts " + stringify(values))

    def cd(self, path=None):
        if path:
            self.eval("cd " + stringify(path))
        else:
            self.eval("cd")

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
            self.eval("unset -nocomplain -- " + join(names))
        else:
            self.eval("unset " + join(names))

    @property
    def stdout(self):
        return self.communicator.stdout

    @property
    def stderr(self):
        return self.communicator.stderr

    def register_fun(self, name, fun):
        idx = len(self.registered_fun)
        self.registered_fun.append(fun)
        self.eval("::private_pytcldriver_::register_function " +
                  name + " " +
                  str(idx))

    def close(self):
        self.communicator.close()

    def __enter__(self):
        root = self.open()
        return self, root

    def __exit__(self, type, value, traceback):
        self.close()

class Namespace(dict):
    pass

class Array(dict):
    pass
