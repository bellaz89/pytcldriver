namespace eval ::tclinterop_private_ {

  variable code_call   C
  variable code_error  E
  variable code_return R
  variable code_close  D
  variable code_rename N

  variable sock [socket localhost [lindex $argv 0]]
  fconfigure $sock -encoding utf-8 -buffering none


  proc communicate {} {

    variable code_call
    variable code_error
    variable code_return
    variable code_close
    variable code_rename
    variable sock

    while {1} {
      gets $sock request
      puts $request
      set code [string index $request 0]
      set body [string range $request 1 end]

      if { $code == $code_call} {
          if { [catch {set result [uplevel $body]} err] } {
            puts stderr $err
            puts -nonewline $sock $code_error$err
          } else {
            puts -nonewline $sock $code_return$result
          }

      } elseif { $code == $code_error} {
          error $body

      } elseif { $code == $code_return} {
          return $body

      } elseif { $code == $code_close} {
          close $sock
          uplevel ::tclinterop_private_::exit $body

      } else {
          set err "The python side unexpectedly returned the code $code with body $body"
          puts -nonewline $sock $code_error$err
          error $err
      }
    }
  }
}



rename exit ::tclinterop_private_::exit

proc exit {returnCode} {
  close $::tclinterop_private_::sock
  set msg $::tclinterop_private::code_close
  append msg "The application prematurely returned with code "
  append msg $returnCode"
  puts -nonewline $::tclinterop_private_::sock $msg
  ::tclinterop_private_::exit $returnCode
}

rename rename ::tclinterop_private_::rename

proc rename {orig target} {
  puts "Hello"
  set msg $::tclinterop_private_::code_rename
  append msg [list $orig $target]
  puts -nonewline $::tclinterop_private_::sock$msg
  ::tclinterop_private_::rename $orig $target
}


exit [::tclinterop_private_::communicate]
