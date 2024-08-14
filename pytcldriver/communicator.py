import socket
import struct
from subprocess import Popen, PIPE
import binascii
import atexit
import shlex
from .tcl import TCL_MAIN_PATH

RANDOM_SIZE=16
PACKET_SIZE=1024
POPEN_CLOSE_TIMEOUT=5.0

class Communicator(object):
    def __init__(self, command, env=None, redirect_stdout=False, port=None):

        self.fragment = bytes()
        self.process = None
        self.stdout = ""
        self.stderr = ""
        self.socket = None

        self.command = command
        self.env = env
        self.redirect_stdout = redirect_stdout
        self.port = port

    def open(self):
        atexit.register(self.close)
        self.fragment = bytes()
        self.stdout = ""
        self.stderr = ""

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if self.port == None:
            self.socket.bind(('', 0))
        elif isinstance(self.port, int):
            self.socket.bind(('', self.port))
        else:
            for i, port in enumerate(self.port):
                try:
                    self.socket.bind(('', port))
                except socket.error as error:
                    if i+1 == len(self.port):
                        raise error

                    continue

        self.socket.listen(1)
        port = self.socket.getsockname()[1]
        tcl_args = str(port)
        args = shlex.split(self.command.format(script=TCL_MAIN_PATH,
                                               tcl_args=tcl_args))

        if self.redirect_stdout:
            self.process = Popen(args,
                                 stderr=PIPE,
                                 stdout=PIPE,
                                 env=self.env)
        else:
            self.process = Popen(args,
                                 env=self.env)

        self.ctrl, self.address = self.socket.accept()

    def send(self, message):
        data = self.encrypt(message)
        data_len = len(data)
        data_len = "%16x" % data_len
        data_len = data_len.encode("utf-8")
        self.ctrl.send(data_len)
        self.ctrl.send(data)

    def receive_bytes(self, num):
        while len(self.fragment) < num:
            self.fragment += self.ctrl.recv(PACKET_SIZE)

        data = self.fragment[:num]
        self.fragment = self.fragment[num:]
        return data

    def receive(self):
        data_len = self.receive_bytes(16)
        data_len = data_len.decode("utf-8")
        data_len = int(data_len, 16)
        data = self.receive_bytes(data_len)
        return self.decrypt(data)

    def encrypt(self, message):
        return message.encode()

    def decrypt(self, data):
        return data.decode("utf-8")

    def check_alive(self):
        return self.process.poll()

    def close(self):
        try:
            self.send("exit 0")
        except:
            pass

        try:
            self.process.wait(timeout=POPEN_CLOSE_TIMEOUT)
            if self.check_alive() is not None:
                self.process.kill()
        except:
            pass

        try:
            self.socket.close()
        except:
            pass

        self.socket = None

        if self.redirect_stdout:
            self.stdout = self.process.stdout.read().decode("utf-8")
            self.stderr = self.process.stderr.read().decode("utf-8")
        else:
            self.stdout = ""
            self.stderr = ""

        self.process = None

        atexit.unregister(self.close)
