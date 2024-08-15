set script_dir [file dirname $::argv0]
source [file join $script_dir communicator.tcl]

set fp [open [file join $script_dir args] "r"]
gets $fp arguments
close $fp
unset fp

# Remove to prevent the encryption key to be readable
file delete [file join $script_dir args]
unset script_dir

::private_pytcldriver_::init $arguments
::private_pytcldriver_::open_connection
::private_pytcldriver_::communicate
