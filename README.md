Python Tcl driver
=================

This library bridges python with Tcl through sockets. The scope is to allow
the control of embedded tcl interpreters by python. This can be
useful for closed source software that is stuck with older version
of the Tcl interpreter and therefore cannot use modern Tcl packages.
`pytcldriver` exposes all defined Tcl methods variable and namespaces to python
thanks to Tcl introspection capabilities.
Wrappers are also provided to give a pythonic interface to basic Tcl types like
numbers, strings, lists, arrays and dictionaries.

Installation
------------

Examples
--------

Mantainers
----------
