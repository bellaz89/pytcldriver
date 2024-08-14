import socket
import struct
from subprocess import Popen, PIPE
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Hash import MD5
import binascii
import atexit

RANDOM_SIZE=16
PACKET_SIZE=1024
LEN_SIZE=8
LEN_MD5=16
POPEN_CLOSE_TIMEOUT=5.0

class Communicator(object):
    def __init__(self, command, env=None,
                 redirect_stdout=False, encrypt_data=False,
                 port=None):

        self.fragment = bytes()
        self.process = None
        self.stdout = ""
        self.stderr = ""
        self.port = port

        if encrypt_data:
            self.aes_key = get_random_bytes(RANDOM_SIZE)

        self.encrypt_data = encrypt_data

        self.socket = None

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

        if encrypt_data:
            tcl_seed = get_random_bytes(RANDOM_SIZE)
            tcl_args += " " + binascii.hexlify(aes_key)
            tcl_args += " " + binascii.hexlify(tcl_seed)

        args = shlex.split(command.format(tcl_args=tcl_args))
        self.redirect_stdout = redirect_stdout

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
        data_md5 = MD5.new(data).digest()
        data_len = len(data)
        data_len = data_len.to_bytes(LEN_SIZE, "big")
        self.ctrl.send(data_len)
        self.ctrl.send(data_md5)
        self.ctrl.send(data)

    def receive(self):
        data_len = self.receive_bytes(LEN_SIZE)
        data_len = int.from_bytes(data_len, "big")
        data_md5 = self.receive_bytes(LEN_MD5)
        data = self.receive_bytes(data_len)

        if MD5.new(data).digest() != data_md5:
            print("MD5 python does not match")
            #raise RuntimeError("Received hash does not match the computed one")

        return self.decrypt(data)

    def receive_bytes(self, num):
        while len(self.fragment) < num:
            self.fragment += self.ctrl.recv(PACKET_SIZE)

        data = self.fragment[:num]
        self.fragment = self.fragment[num:]
        return data

    def encrypt(self, message):
        data = message.encode()
        if self.encrypt_data:
            iv = get_random_bytes(RANDOM_SIZE)
            cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
            pad = cipher.block_size - (len(data) % cipher.block_size)

            if pad == 0:
                pad = cipher.block_size

            data += pad.to_bytes(1, "big") * pad
            return iv + cipher.encrypt(data)
        else:
            return encoded

    def decrypt(self, data):
        if self.encrypt_data:
            iv = data[:RANDOM_SIZE]
            cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
            data = data[RANDOM_SIZE:]
            data = cipher.decrypt(data)
            data = data[:-data[-1]]

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

        self.process = None

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

        atexit.unregister(self.close)
