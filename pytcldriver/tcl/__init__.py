from importlib_resources import files
import tempfile
import atexit
import shutil
import os

TEMPFILE_DIRECTORY = tempfile.TemporaryDirectory(prefix="pytcldriver.")
atexit.register(TEMPFILE_DIRECTORY.cleanup)

TCL_SOURCES_DIRECTORY = TEMPFILE_DIRECTORY.name
os.mkdir(os.path.join(TCL_SOURCES_DIRECTORY, "aes"))
os.mkdir(os.path.join(TCL_SOURCES_DIRECTORY, "md5"))

for tcl_file in files("pytcldriver.tcl"):
    print(str(tcl_file))

TCL_MAIN_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "main.tcl")
TCL_COMM_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "communicator.tcl")
TCL_DICT_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "dict.tcl")

