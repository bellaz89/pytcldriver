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

path = files("pytcldriver.tcl")
for root, dirs, tcl_files in os.walk(path):
    for tcl_file in tcl_files:
        shutil.copyfile(os.path.join(root, tcl_file),
                        os.path.join(TCL_SOURCES_DIRECTORY, tcl_file))
    break

path = files("pytcldriver.tcl.aes")
for root, dirs, tcl_files in os.walk(path):
    for tcl_file in tcl_files:
        shutil.copyfile(os.path.join(root, tcl_file),
                        os.path.join(TCL_SOURCES_DIRECTORY, "aes", tcl_file))
    break

path = files("pytcldriver.tcl.md5")
for root, dirs, tcl_files in os.walk(path):
    for tcl_file in tcl_files:
        shutil.copyfile(os.path.join(root, tcl_file),
                        os.path.join(TCL_SOURCES_DIRECTORY, "md5", tcl_file))
    break

TCL_MAIN_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "main.tcl")
TCL_COMM_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "communicator.tcl")
TCL_DICT_PATH = os.path.join(TCL_SOURCES_DIRECTORY, "dict.tcl")

