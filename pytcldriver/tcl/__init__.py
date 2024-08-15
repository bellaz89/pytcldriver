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

