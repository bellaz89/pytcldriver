from tclinterop import Interpreter
import subprocess
import shutil
import shlex
from pathlib import Path

class Xilinx(Interpreter):
    def __init__(self, program_dir=None, source_env=True, env=dict()):
        if program_dir:
            self.program_dir = program_dir
        else:
            self.program_dir = self.find_program_dir()

        env = dict(env)
        if source_env:
            env.update(self.source_env())

        super(Xilinx, self).__init__(self.fullpath_bin(), env)

    def source_env(self):

        env = dict()
        full_path = str(Path(self.program_dir).joinpath("settings64.sh"))
        command = shlex.split("bash -c 'source {} && env'".format(full_path))
        proc = subprocess.Popen(command, stdout = subprocess.PIPE)

        for line in proc.stdout.read().decode("utf-8").split("\n"):
          (key, _, value) = line.partition("=")
          env[key] = value

        proc.communicate()

        return env

    def fullpath_bin(self):
        return str(Path(self.program_dir).joinpath(self.local_bin()))

    def local_bin(self):
        pass

    def find_program_dir(self):
        pass


class Vivado(Xilinx):
    def local_bin(self):
        return "bin/vivado -mode batch -source comm.tcl -tclargs {port}"

    def find_program_dir(self):
        return Path(shutil.which("vivado")).parents[1]

class Vitis(Xilinx):
    def local_bin(self):
        return "bin/xsct comm.tcl {port}"

    def find_program_dir(self):
        return Path(shutil.which("vitis")).parents[1]

class ISE(Xilinx):
    def local_bin(self):
        return "ISE/bin/lin64/xtclsh comm.tcl {port}"

    def find_program_dir(self):
        return Path(shutil.which("ise")).parents[3]

class PlanAhead(Xilinx):
    def local_bin(self):
        return "PlanAhead/bin/planAhead -mode batch -source comm.tcl -tclargs {port}"

    def find_program_dir(self):
        return Path(shutil.which("planAhead")).parents[2]
