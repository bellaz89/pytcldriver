rename exit exit_

proc exit {{returnCode}} {
  close $::tclinterop_private_::sock
  set msg $::tclinterop_private::code_close
  append msg "The application prematurely returned with code "
  append msg $returnCode"
  puts -nonewline $::tclinterop_private_::sock $msg
  exit_ returnCode
}

namespace eval ::tclinterop_private_ {

  set code_call   C
  set code_error  E
  set code_return R
  set code_close  D

  set sock [socket localhost [lindex $argv 0]]
  fconfigure $sock -encoding utf-8 -buffering none

  while {1} {
    gets $sock request
    set code [string index $request 0]
    set body [string range $request 1 end]

    if { $code == $code_call} {
        if { [catch {set result [uplevel #0 $body]} err] } {
          puts stderr $err
          puts -nonewline $sock $code_error$err
        } else {
          puts -nonewline $sock $code_return$result
        }

      } elseif { $code == $code_error} {
        throw INTEROP $body

      } elseif { $code == $code_return} {
        set err "The python side unexpectedly returned the value $body"
        puts -nonewline $sock $code_error$err
        throw UNEXPECTED_RETURN $err

      } elseif { $code == $code_close} {
        close $sock
        uplevel #0 exit_ $body

      } else {
        set err "The python side unexpectedly returned the code $code with body $body"
        puts -nonewline $sock $code_error$err
        throw UNEXPECTED_CODE $err
      }
    }
  }
}
