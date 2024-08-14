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

```
  pip install git+https://github.com/bellaz89/pytcldriver.git
```

Examples
--------

```python
  from pytcldriver import Interpreter, Namespace

  interp = Interpreter()
  # Returns the namespace '::'
  tcl_namespace = interp.open()

  # Tcl methods can be directly called from the namespace
  tcl_namespace.expr("1", "+", "1")

  tcl_namespace.a = 12 # Tcl variable in '::'
  print(tcl_namespace.a)
  tcl_namespace.a.num += 2
  print(tcl_namespace.a)

  # Use dir to see all the defined variables, methods and namespace defined
  # in the Tcl interpreter
  dir(tcl_namespace)

  # Methods can be also explicitly called
  interp.eval("list 1 2 3")

  # It is possible to register a function callable from tcl
  tcl_namespace.add1 = lambda x: float(x) + 1
  print(tcl_namespace.add1(10))

  # Requires Vivado installed
  from pytcldriver.xilinx import Vivado
  interp = Vivado()
  tcl_namespace = interp.open() # Returns the namespace '::'
  print(tcl_namespace.version(), "\n")

  # Requires ISE installed
  from pytcldriver.xilinx import ISE
  interp.open()

  # Requires PlanAhead installed
  from pytcldriver.xilinx import PlanAhead
  interp = PlanAhead()
  tcl_namespace = interp.open() # Returns the namespace '::'
  print(tcl_namespace.version(), "\n")

  # Requires Vitis installed
  from pytcldriver.xilinx import Vitis
  interp = Vitis()
  tcl_namespace = interp.open() # Returns the namespace '::'
  print(tcl_namespace.version(), "\n")
```

Mantainers
----------

Andrea Bellandi (andrea.bellandi@desy.de)
