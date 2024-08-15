from importlib_resources import files
import tempfile
import atexit
import shutil
import os

class ResourcesDirectory(object):
    def __init__(self):
        self.directory = tempfile.TemporaryDirectory(prefix="pytcldriver.")
        atexit.register(self.directory.cleanup)

        tcl_sources_directory = self.directory.name
        tcl_sources_base64_directory = os.path.join(tcl_sources_directory, "base64")
        tcl_sources_aes_directory = os.path.join(tcl_sources_directory, "aes")

        os.mkdir(tcl_sources_base64_directory)
        os.mkdir(tcl_sources_aes_directory)

        resource_path = files("pytcldriver.tcl")

        for name in ["main_shell.tcl", "main_file.tcl", "communicator.tcl",
                     "dict.tcl", "mt19937.tcl"]:

            with open(os.path.join(tcl_sources_directory, name), "w") as f:
                f.write(resource_path.joinpath(name).read_text())

        resource_base64_path = files("pytcldriver.tcl.base64")

        for name in ["pkgIndex.tcl", "base64.tcl", "base64c.tcl"]:
            with open(os.path.join(tcl_sources_base64_directory, name), "w") as f:
                f.write(resource_base64_path.joinpath(name).read_text())

        resource_aes_path = files("pytcldriver.tcl.aes")

        for name in ["pkgIndex.tcl", "aes.tcl"]:
            with open(os.path.join(tcl_sources_aes_directory, name), "w") as f:
                f.write(resource_aes_path.joinpath(name).read_text())

        self.resources_path = self.directory.name
        self.main_shell_path = os.path.join(tcl_sources_directory, "main_shell.tcl")
        self.main_file_path = os.path.join(tcl_sources_directory, "main_file.tcl")
        self.pipe_p2t = os.path.join(tcl_sources_directory, "pipe_p2t")
        self.pipe_t2p = os.path.join(tcl_sources_directory, "pipe_t2p")

    def close(self):
        self.directory.cleanup()
        atexit.unregister(self.directory.cleanup)

