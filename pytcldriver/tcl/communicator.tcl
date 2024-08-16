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

namespace eval ::private_pytcldriver_ {
  variable port ""
  variable fp_p2t ""
  variable fp_t2p ""
  variable aes_key ""
  variable prng ""
  variable recv_data ""
  variable comm_stack 0
  variable script_dir [file dirname $::argv0]
  source [file join $script_dir mt19937.tcl]
}

source [file join $script_dir dict.tcl]

if {[catch {package require base64} err]} {
  set dir [file join $::private_pytcldriver_::script_dir base64]
  source [file join $dir pkgIndex.tcl]
  package require base64
  unset dir
}

if {[catch {package require aes} err]} {
  set dir [file join $::private_pytcldriver_::script_dir aes]
  source [file join $dir pkgIndex.tcl]
  package require aes
  unset dir
}

proc ::private_pytcldriver_::init {params} {
  variable port [lindex $params 0]
  if {[llength $params] > 1} {
     variable aes_key [binary format H* [lindex $params 1]]
     mt::seed "0x[lindex $params 2]"
  }
}

proc ::private_pytcldriver_::rekey {new_key new_seed} {
  variable aes_key [binary format H* $new_key]
  mt::seed "0x$new_seed"
  return 1
}

proc ::private_pytcldriver_::new_iv {} {
  set result ""
  append result [binary format I [mt::int32]]
  append result [binary format I [mt::int32]]
  append result [binary format I [mt::int32]]
  append result [binary format I [mt::int32]]
  return $result
}

proc ::private_pytcldriver_::pad_extend {pad} {
  set ext ""
  set N [expr $pad / 4]

  for {set i 0} {$i < $N} {incr i} {
    append ext [binary format I [mt::int32]]
  }

  set N [expr $pad % 4]

  for {set i 0} {$i < $N } {incr i} {
    append ext [binary format c [expr [mt::int32] % 0xff]]
  }

  return $ext
}

proc ::private_pytcldriver_::open_connection {} {
  variable port
  variable fp_p2t
  variable fp_t2p
  variable script_dir

  if {$port == "pipe"} {
    set fp_p2t [open [file join $script_dir pipe_p2t] "r"]
    set fp_t2p [open [file join $script_dir pipe_t2p] "w"]
  } else {
    set sock [socket localhost $port]
    fconfigure $sock -translation binary
    set fp_p2t $sock
    set fp_t2p $sock
  }
}

proc ::private_pytcldriver_::send {data} {
  variable fp_t2p
  set data [encrypt $data]
  set data_len [string bytelength $data]
  set data_len [format %16x $data_len]
  set data_len [encoding convertto utf-8 $data_len]
  puts -nonewline $fp_t2p $data_len
  puts -nonewline $fp_t2p $data
  flush $fp_t2p
}

proc ::private_pytcldriver_::receive_bytes {num} {
  variable fp_p2t
  variable recv_data

  while {$num > [string bytelength $recv_data]} {
    set diff [expr $num - [string bytelength $recv_data]]
    set received [read $fp_p2t $diff]
    append recv_data $received
  }

  set format_string a$num
  append format_string a*
  binary scan $recv_data $format_string result recv_data

  return $result
}

proc ::private_pytcldriver_::receive {} {
  set data_len [receive_bytes 16]
  set data_len [encoding convertfrom utf-8 $data_len]
  set data_len [scan $data_len %x]
  set data [receive_bytes $data_len]
  return [decrypt $data]
}

proc ::private_pytcldriver_::encrypt {data} {
  variable aes_key

  set data [encoding convertto utf-8 $data]

  if {$aes_key != ""} {
    set iv [new_iv]
    set pad [expr 16 - ([string bytelength $data] % 16)]
    append data [pad_extend $pad]
    set pad [binary format c $pad]
    set data [::aes::aes -mode cbc -dir encrypt -key $aes_key -iv $iv -- $data]
    set data "$pad$iv$data"
  }

  set data [::base64::encode -wrapchar "" $data]

  return $data
}

proc ::private_pytcldriver_::decrypt {data} {
  variable aes_key

  set data [::base64::decode $data]

  if {$aes_key != ""} {
    binary scan $data ca16a* pad iv data
    set data [::aes::aes -mode cbc -dir decrypt -key $aes_key -iv $iv -- $data]
    set format_string "a[expr [string bytelength $data] - $pad]a$pad"
    binary scan $data $format_string data pad
  }

  set data [encoding convertfrom utf-8 $data]

  return $data
}

proc ::private_pytcldriver_::close_connection {} {
  variable socket_inst
  close $socket_inst
}

proc ::private_pytcldriver_::register_function {name idx} {
  proc $name {args} "
    set fun_name \[lindex \[info level 0\] 0\];
    set ns_caller \[uplevel {namespace current}\];
    set data \[linsert \$args 0 \$fun_name \$ns_caller \];
    ::private_pytcldriver_::send \"call $idx \$data\";
    ::private_pytcldriver_::communicate
  "
}

rename ::exit ::private_pytcldriver_::exit_

proc ::exit {{retval 0}} {
  ::private_pytcldriver_::send "exit $retval"

  if {$::private_pytcldriver_::fp_p2t != $::private_pytcldriver_::fp_t2p} {
    close $::private_pytcldriver_::fp_p2t
    close $::private_pytcldriver_::fp_t2p
  } else {
    close $::private_pytcldriver_::fp_t2p
  }

  ::private_pytcldriver_::exit_ $retval
}

proc ::private_pytcldriver_::communicate {} {
  variable comm_stack
  incr comm_stack 1

  while {1} {
    set data [receive]
    set cmd [lindex $data 0]
    if {($cmd == "error") || ($cmd == "return")} {
      incr comm_stack -1
      uplevel $data
    } elseif {[catch {set result [uplevel $data]} err]} {
      send "error \{$err\}"
    } else {
      send "return $result"
    }
  }
}

