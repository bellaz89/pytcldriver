from interpreter import Interpreter
import subprocess
import shutil
import shlex
from pathlib import Path

class Xilinx(Interpreter):
    def __init__(self, program_dir=None, source_env=True, **kwargs):
        if program_dir:
            self.program_dir = program_dir
        else:
            self.program_dir = self.find_program_dir()

        program = str(Path(self.program_dir).joinpath(self.local_bin()))
        cmd = "bash -c '{}'".format(program)

        if source_env:
            settings_path = str(Path(self.program_dir).joinpath("settings64.sh"))
            cmd = "bash -c 'source {} && {}'".format(settings_path,
                                                     program)

        super(Xilinx, self).__init__(cmd, **kwargs)

    def local_bin(self):
        pass

    def find_program_dir(self):
        pass


class Vivado(Xilinx):
    def local_bin(self):
        return "bin/vivado -mode batch -source comm.tcl -tclargs {tcl_args}"

    def find_program_dir(self):
        return Path(shutil.which("vivado")).parents[1]


class Vitis(Xilinx):
    def local_bin(self):
        return "bin/xsct comm.tcl {tcl_args}"

    def find_program_dir(self):
        return Path(shutil.which("vitis")).parents[1]


class ISE(Xilinx):
    def local_bin(self):
        return "ISE/bin/lin64/xtclsh comm.tcl {tcl_args}"

    def find_program_dir(self):
        return Path(shutil.which("ise")).parents[3]


class PlanAhead(Xilinx):
    def local_bin(self):
        return "PlanAhead/bin/planAhead -mode batch -source comm.tcl -tclargs {tcl_args}"

    def find_program_dir(self):
        return Path(shutil.which("planAhead")).parents[2]


