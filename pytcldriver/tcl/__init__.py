from importlib_resources import files
import tempfile
import atexit
import shutil
import os

TEMPFILE_DIRECTORY = tempfile.TemporaryDirectory(prefix="pytcldriver.")
atexit.register(TEMPFILE_DIRECTORY.cleanup)

TCL_SOURCES_DIRECTORY = TEMPFILE_DIRECTORY.name

RESOURCE_PATH = files("pytcldriver.tcl")
RESOURCE_MAIN = RESOURCE_PATH.joinpath("main.tcl")
RESOURCE_COMM = RESOURCE_PATH.joinpath("communicator.tcl")
RESOURCE_DICT = RESOURCE_PATH.joinpath("dict.tcl")

with open(os.path.join(TCL_SOURCES_DIRECTORY, "main.tcl"), "w") as f:
    f.write(RESOURCE_MAIN.read_text())

with open(os.path.join(TCL_SOURCES_DIRECTORY, "communicator.tcl"), "w") as f:
    f.write(RESOURCE_COMM.read_text())

with open(os.path.join(TCL_SOURCES_DIRECTORY, "dict.tcl"), "w") as f:
    f.write(RESOURCE_DICT.read_text())

TCL_MAIN_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "main.tcl")
TCL_COMM_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "communicator.tcl")
TCL_DICT_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "dict.tcl")

