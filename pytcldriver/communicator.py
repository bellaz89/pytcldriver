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
    def __init__(self, command, env=None,
                 redirect_stdout=True,
                 communication="auto",
                 port=None,
                 encrypt_data=True,
                 args_passing="file"):

        self.fragment = bytes()
        self.process = None
        self.stdout = ""
        self.stderr = ""
        self.socket = None
        self.resources = None
        self.aes_key = None
        self.pipe_p2t = None
        self.pipe_t2p = None

        self.command = command
        self.env = env
        self.redirect_stdout = redirect_stdout
        self.port = port
        self.encrypt_data = encrypt_data
        self.args_passing = args_passing

        if communication == "auto":
            if os.name == "posix":
                communication = "pipe"
            else:
                communication = "socket"

        self.communication = communication

    def open(self):
        atexit.register(self.close)
        self.fragment = bytes()
        self.stdout = ""
        self.stderr = ""
        self.resources = ResourcesDirectory()

        if self.encrypt_data:
            self.aes_key = get_random_bytes(16)
        else:
            self.aes_key = None

        tcl_args = None

        if self.communication == "socket":
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

            port = self.socket.getsockname()[1]
            self.socket.listen(1)
            tcl_args = str(port)

        elif self.communication == "pipe":
            os.mkfifo(self.resources.pipe_p2t, mode=0o600)
            os.mkfifo(self.resources.pipe_t2p, mode=0o600)
            tcl_args = "pipe"

        else:
            self.close()
            raise Exception("Unknown communication method. " \
                            "Choose either 'socket' or 'pipe'")


        if self.encrypt_data:
            tcl_args += " " + self.aes_key.hex()
            tcl_args += " " + get_random_bytes(8).hex()

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

        if self.communication == "socket":
            self.ctrl, self.address = self.socket.accept()

        if self.communication == "pipe":
            self.pipe_p2t = open(self.resources.pipe_p2t, "wb")
            self.pipe_t2p = open(self.resources.pipe_t2p, "rb")

        if self.encrypt_data:
            aes_key = get_random_bytes(16)
            self.send("::private_pytcldriver_::rekey " +
                      aes_key.hex() + " " +
                      get_random_bytes(8).hex())

            self.aes_key = aes_key
            assert self.receive() == "return 1"

    def send(self, message):
        data = self.encrypt(message)
        data_len = len(data)
        data_len = "%16x" % data_len
        data_len = data_len.encode("utf-8")
        data = data_len + data

        if self.communication == "socket":
            self.ctrl.send(data)

        if self.communication == "pipe":
            self.pipe_p2t.write(data)
            self.pipe_p2t.flush()

    def receive_bytes(self, num):
        if self.communication == "socket":
            while len(self.fragment) < num:
                self.fragment += self.ctrl.recv(PACKET_SIZE)

        if self.communication == "pipe":
            self.fragment += self.pipe_t2p.read(num - len(self.fragment))

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
            if self.check_alive() == None:
                self.process.kill()
        except:
            pass

        if self.communication == "socket":
            try:
                self.socket.close()
            except:
                pass

            try:
                self.resources.close()
            except:
                pass

        if self.communication == "pipe":
            try:
                self.pipe_p2t.close()
                self.pipe_t2p.close()
                os.remove(self.resources.pipe_p2t)
                os.remove(self.resources.pipe_t2p)
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
