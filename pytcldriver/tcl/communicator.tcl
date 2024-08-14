variable socket_port ""
variable socket_inst ""
variable aes_key ""
variable prng ""
variable recv_data ""
variable aes_blocksize 16
variable comm_stack 0

set script_dir [file dirname $::argv0]
source [file join $script_dir dict.tcl]

if {[catch {package require base64} err]} {
  set dir [file join $script_dir base64]
  source [file join $dir pkgIndex.tcl]
  package require base64
  unset dir
}

unset script_dir

proc init {params} {
  variable socket_port [lindex $params 0]
}

proc open_connection {} {
  variable socket_port
  variable socket_inst [socket localhost $socket_port]
  fconfigure $socket_inst -translation binary
}

proc send {data} {
  variable socket_inst
  set data [encrypt $data]
  set data_len [string bytelength $data]
  set data_len [format %16x $data_len]
  set data_len [encoding convertto utf-8 $data_len]
  puts -nonewline $socket_inst $data_len
  flush $socket_inst
  puts -nonewline $socket_inst $data
  flush $socket_inst
}

proc receive_bytes {num} {
  variable socket_inst
  variable recv_data

  while {$num > [string bytelength $recv_data]} {
    set diff [expr $num - [string bytelength $recv_data]]
    set received [read $socket_inst $diff]
    append recv_data $received
  }

  set format_string a$num
  append format_string a*
  binary scan $recv_data $format_string result recv_data

  return $result
}

proc receive {} {
  set data_len [receive_bytes 16]
  set data_len [encoding convertfrom utf-8 $data_len]
  set data_len [scan $data_len %x]
  set data [receive_bytes $data_len]
  return [decrypt $data]
}

proc encrypt {data} {
  set data [encoding convertto utf-8 $data]
  set data [::base64::encode -wrapchar "" $data]
  return $data
}

proc decrypt {data} {
  set data [::base64::decode $data]
  set data [encoding convertfrom utf-8 $data]
  return $data
}

proc close_connection {} {
  variable socket_inst
  close $socket_inst
}

proc register_function {name idx} {
  proc $name {args} "
    send \"call $idx \$args\";
    communicate
  "
}

rename ::exit exit_

proc ::exit {{retval 0}} {
  send "exit $retval"
  exit_ $retval
}

proc communicate {} {
  variable comm_stack
  incr comm_stack 1

  while {1} {
    set data [receive]
    set cmd [lindex $data 0]
    if {($cmd == "error") || ($cmd == "return")} {
      incr comm_stack -1
      uplevel $data
    } elseif {[catch {set result [uplevel $data]} err]} {
      send "error $err"
    } else {
      send "return $result"
    }
  }
}

