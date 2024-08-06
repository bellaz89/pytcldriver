from subprocess import Popen, PIPE
import shlex
import socket
import atexit

from wrappers import NamespaceWrapper
from utils import info_tclversion, join, stringify

FUN_SRC = "proc {} {{args}} {{" \
"    set sock $::tclinterop_private_::sock;" \
"    set fname [lindex [info level 0] 0];" \
"    puts -nonewline $sock [concat $::tclinterop_private_::code_call $fname $args];" \
"    return [::tclinterop_private_::communicate]" \
"}}"

class Interpreter:
    MAX_MSG_SIZE=16384
    CODE_CALL="C"
    CODE_ERROR="E"
    CODE_RETURN="R"
    CODE_CLOSE="D"
    CODE_RENAME="N"

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
        self.eval("source dict.tcl") # For older versions of TCL

        return NamespaceWrapper(self)

    def _save_stdout(self):
        self.stdout = self.process.stdout.read().decode("utf-8")
        self.stderr = self.process.stderr.read().decode("utf-8")

    def _check_alive(self):
        poll = self.process.poll()
        if poll:
            atexit.unregister(self.exit)
            self.socket.close()
            self._save_stdout()
            self.process = None
            err = "The interpreter prematurely exited with code " + str(poll)
            raise RuntimeError(err)

    def _eval(self, fun):
        if self.is_running() is False:
            err = "Call .open() before interacting with the interpreter"
            raise RuntimeError(err)

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
                raise RuntimeError("While executing .eval(\"" + fun +
                                   "\"):\n" + body)

            elif code == self.CODE_ERROR:
                raise RuntimeError("While executing .eval(\"" + fun +
                                   "\"):\n" + body)

            elif code == self.CODE_RENAME:
                [old, new] = body.split(" ", 1)
                if old in self.registered_fun:
                    fun = self.registered_fun
                    del registered_fun[old]
                    registered_fun[new] = fun

            else:
                assert code == self.CODE_CALL
                try:
                    [fun_id, args] = body[1:].split(" ", 1)
                    args = [self.list_get(args, i)
                            for i
                            in range(self.list_size(args))]

                    retval = self.registered_fun[fun_id](*args)
                    retval = stringify(retval)
                except Exception as err:
                    self.ctrl.send((self.CODE_ERROR + str(err) +
                                    "\n").encode())
                else:
                    self.ctrl.send((self.CODE_RETURN + retval +
                                    "\n").encode())

    def eval(self, fun, *args):
        fun_str = (fun + " " + join(args)).strip()
        self.command_list.append(fun_str)
        return self._eval(fun_str)

    @property
    def version(self):
        return info_tclversion(self)

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

    def get_stdout(self):
        return self.stdout

    def get_stderr(self):
        return self.stderr

    def is_running(self):
        return self.process is not None

    def register_fun(self, name, fun):
        self.registered_fun[name] = fun
        self.eval(FUN_SRC.format(name))

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

class Namespace(dict):
    pass

class Array(dict):
    pass
