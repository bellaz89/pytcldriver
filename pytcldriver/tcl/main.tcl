set script_dir [file dirname $::argv0]
source [file join $script_dir communicator.tcl]
unset script_dir

init $argv
open_connection
communicate
