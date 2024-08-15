set script_dir [file dirname $::argv0]
source [file join $script_dir communicator.tcl]
unset script_dir

::private_pytcldriver_::init $argv
::private_pytcldriver_::open_connection
::private_pytcldriver_::communicate
