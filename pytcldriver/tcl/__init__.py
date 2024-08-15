from importlib_resources import files
import tempfile
import atexit
import shutil
import os

TEMPFILE_DIRECTORY = tempfile.TemporaryDirectory(prefix="pytcldriver.")
atexit.register(TEMPFILE_DIRECTORY.cleanup)

TCL_SOURCES_DIRECTORY = TEMPFILE_DIRECTORY.name
TCL_SOURCES_BASE64_DIRECTORY = os.path.join(TCL_SOURCES_DIRECTORY, "base64")
TCL_SOURCES_AES_DIRECTORY = os.path.join(TCL_SOURCES_DIRECTORY, "aes")

os.mkdir(TCL_SOURCES_BASE64_DIRECTORY)
os.mkdir(TCL_SOURCES_AES_DIRECTORY)

RESOURCE_PATH = files("pytcldriver.tcl")
RESOURCE_MAIN = RESOURCE_PATH.joinpath("main.tcl")
RESOURCE_COMM = RESOURCE_PATH.joinpath("communicator.tcl")
RESOURCE_DICT = RESOURCE_PATH.joinpath("dict.tcl")

for name in ["main.tcl", "communicator.tcl", "dict.tcl", "mt19937.tcl"]:
    with open(os.path.join(TCL_SOURCES_DIRECTORY, name), "w") as f:
        f.write(RESOURCE_PATH.joinpath(name).read_text())

RESOURCE_BASE64_PATH = files("pytcldriver.tcl.base64")

for name in ["pkgIndex.tcl", "base64.tcl", "base64c.tcl"]:
    with open(os.path.join(TCL_SOURCES_BASE64_DIRECTORY, name), "w") as f:
        f.write(RESOURCE_BASE64_PATH.joinpath(name).read_text())

RESOURCE_AES_PATH = files("pytcldriver.tcl.aes")

for name in ["pkgIndex.tcl", "aes.tcl"]:
    with open(os.path.join(TCL_SOURCES_AES_DIRECTORY, name), "w") as f:
        f.write(RESOURCE_AES_PATH.joinpath(name).read_text())

TCL_MAIN_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "main.tcl")
TCL_COMM_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "communicator.tcl")
TCL_DICT_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "dict.tcl")

