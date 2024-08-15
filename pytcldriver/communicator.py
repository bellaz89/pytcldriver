import socket
from subprocess import Popen, PIPE
from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import atexit
import shlex
from .tcl import ResourcesDirectory
import os

PACKET_SIZE=1024
POPEN_CLOSE_TIMEOUT=5.0

class Communicator(object):
    def __init__(self, command, env=None, redirect_stdout=True, port=None,
                 encrypt_data=True, args_passing="file"):

        self.fragment = bytes()
        self.process = None
        self.stdout = ""
        self.stderr = ""
        self.socket = None
        self.resources = None
        self.aes_key = None

        self.command = command
        self.env = env
        self.redirect_stdout = redirect_stdout
        self.port = port
        self.encrypt_data = encrypt_data
        self.args_passing = args_passing

    def open(self):
        atexit.register(self.close)
        self.fragment = bytes()
        self.stdout = ""
        self.stderr = ""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if self.encrypt_data:
            self.aes_key = get_random_bytes(16)
        else:
            self.aes_key = None

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

        if self.encrypt_data:
            tcl_args += " " + self.aes_key.hex()
            tcl_args += " " + get_random_bytes(8).hex()

        self.resources = ResourcesDirectory()

        if self.args_passing == "shell":
            args = shlex.split(self.command.format(script=self.resources.main_shell_path,
                                                   tcl_args=tcl_args))
        elif self.args_passing == "file":
            args = shlex.split(self.command.format(script=self.resources.main_file_path,
                                                   tcl_args=""))

            with open(os.path.join(self.resources.resources_path,
                                   "args"), 'w') as f:
                f.write(tcl_args + "\n")
        else:
            self.close()
            raise Exception("Unknown argument passing style. " \
                            "Choose either 'file' or 'shell'")

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
        data = message.encode()

        if self.encrypt_data:
            iv = get_random_bytes(16)
            cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
            pad = 16 - (len(data) % 16)
            pad_ext = get_random_bytes(pad)
            pad_ext = bytes([48 + b % 64 for b in pad_ext])
            data += pad_ext
            data = pad.to_bytes(1, "big") + cipher.iv + cipher.encrypt(data)

        data = b64encode(data)
        return data

    def decrypt(self, data):
        data = b64decode(data)

        if self.encrypt_data:
            pad = data[0]
            iv = data[1:17]
            data = data[17:]
            cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
            data = cipher.decrypt(data)

            if pad > 0:
                data = data[:-pad]

        data = data.decode("utf-8")
        return data

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

        try:
            self.resources.close()
        except:
            pass

        self.stdout = ""
        self.stderr = ""

        if self.redirect_stdout:
            try:
                    self.stdout = self.process.stdout.read().decode("utf-8")
                    self.stderr = self.process.stderr.read().decode("utf-8")
            except:
                pass

        atexit.unregister(self.close)
