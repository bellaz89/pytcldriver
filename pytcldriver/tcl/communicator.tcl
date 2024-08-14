variable socket_port ""
variable socket_inst ""
variable aes_key ""
variable prng ""
variable aes_blocksize 16

set script_dir [file dirname $::argv0]
source [file join $script_dir dict.tcl]
source [file join $script_dir mt19937.tcl]

if { [catch {package require aes]} {
  set dir [file join $script_dir aes]
  source [file join $script_dir aes/pkgIndex.tcl]
  package require aes
  unset dir
}

if { [catch {package require md5]} {
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
  puts -nonewline $data_len
  puts -nonewline $data_md5
  puts -nonewline $data
  flush $socket_inst
}

proc receive {} {
  variable socket_inst
  binary scan W [read $socket_inst 8] data_len
  set data_md5 [read $socket_inst 16]
  set data [read $socket_inst $data_len]

  if {$data_md5 != [::md5::md5 $data]} {
    puts "MD5 tcl does not match"
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

  set data [binary scan a* $data]
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

proc ::exit {retval} {
  send "exit $retval"
  exit_ $retval
}

proc communicate {} {
  while {1} {
    set data [receive]
    if {[lindex $data 0] == "error"} {
      uplevel $data
    }

    if {[catch [set result [uplevel $data err]]]} {
      send "error $err"
    } else {
      send "return $result"
    }
  }
}

