variable socket_port ""
variable socket_inst ""
variable aes_key ""
variable prng ""
variable recv_data ""
variable aes_blocksize 16
variable comm_stack 0

set script_dir [file dirname $::argv0]
source [file join $script_dir dict.tcl]
source [file join $script_dir mt19937.tcl]

if {[catch {package require aes}]} {
  set dir [file join $script_dir aes]
  source [file join $script_dir aes/pkgIndex.tcl]
  package require aes
  unset dir
}

if {[catch {package require md5}]} {
  set dir [file join $script_dir md5]
  source [file join $script_dir md5/pkgIndex.tcl]
  package require md5
  unset dir
}

unset script_dir

proc init {params} {
  variable socket_port [lindex $params 0]
  if {[llength $params] > 1} {
     variable aes_key [binary format H* [lindex $params 1]]
     mt::seed "0x[lindex $params 2]"
  }
}

proc new_iv {} {
  return [binary format I4 [mt::int32] [mt::int32] [mt::int32] [mt::int32]]
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
  set data_len [binary format W $data_len]
  set data_md5 [::md5::md5 $data]
  puts -nonewline $socket_inst $data_len
  puts -nonewline $socket_inst $data_md5
  puts -nonewline $socket_inst $data
  flush $socket_inst
}

proc receive_bytes {num} {
  variable socket_inst
  variable recv_data

  while {$num > [string bytelength $recv_data]} {
    set diff [expr $num - [string bytelength $recv_data]]
    set received [read $socket_inst $diff]
    #puts $received
    append recv_data $received
  }

  set format_string a$num
  append format_string a*
  binary scan $recv_data $format_string result recv_data

  return $result
}

proc receive {} {
  binary scan [receive_bytes 8] W data_len
  set data_md5 [receive_bytes 16]
  set data [receive_bytes $data_len]

  if {$data_md5 != [::md5::md5 $data]} {
    error "MD5 tcl does not match"
  }

  return [decrypt $data]
}

proc encrypt {data} {
  variable aes_key
  variable aes_blocksize
  set data [encoding convertto utf-8 $data]
  set data [binary format a* $data]

  if {$aes_key != ""} {
    set iv [new_iv]
    set pad [expr $aes_blocksize - ([string bytelength $data] % $aes_blocksize)]
    if {$pad == 0} {
      set pad $aes_blocksize
    }
    set pad [string repeat [binary format c $pad] $pad]
    append data $pad
    set data [::aes::aes -mode cbc -dir encrypt -key $aes_key -iv $iv $data]
  }

  return $data
}

proc decrypt {data} {
  variable aes_key
  variable aes_blocksize

  if {$aes_key != ""} {
    set format_string a$aes_blocksize
    append format_string a*
    binary scan $format_string $data iv data
    set data [::aes::aes -mode cbc -dir decrypt -key $aes_key -iv $iv $data]
    set pad [string range $data end end]
    set pad [binary scan $pad c pad]
    set data [string range $data 0 end-$pad]
  }

  return [encoding convertfrom utf-8 $data]
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

proc ::exit {retval} {
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

