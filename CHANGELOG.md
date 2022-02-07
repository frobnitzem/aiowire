# ChangeLog

## [2.1.0] - 2022-02-07

### Changed

- `Repeat` and `Forever` no longer use `ApplyM` internally.
  This was non-intuitive, and overall decreased usability.
  Now `Repeat` and `Forever` always send the same arguments (if any)
  to their enclosed `Wire`.

- `RepeatM` and `ForeverM` perform wire repetition with
  argument passing.

### Fixed

- `Repeat` called its embedded function with incorrect arguments.
  This has been fixed.


## [2.0.0] - 2022-02-06

This release adds a killer feature -- wires can return
values that are passed on to the next wire.  To use it,
a wire returns a tuple `(newWire, [arg1, arg2, ...])`.  Then
the `EventLoop` will call `await newWire(ev, arg1, arg2, ...)`.

This is backwards-compatible with the older, simpler version.
We also add two new wire types, `Sequence`, and `ApplyM`.
These express composition of wires two different ways.
The first is created with syntax (`wire1 >> wire2`).
It throws away the return values of `wire1` and always calls
`wire2(ev)`.  The second is created with Haskell syntax,
`wire1 >= wire2`.  It passes the return value of `wire1`
into `wire2`'s call.  For example, if `wire1` returns
`(None, [a, ...])`, then wire2 is called as `wire2(ev, a, ...)`.


### Added

- `Sequence` and `ApplyM` classes

### Changed

- Wire-s can now be called with more arguments than just the event loop.
  Accessing this feature requires using a 2-element return tuple, or a
  Repeat, Forever, or ApplyM wire.

- Poller now raises an IndexError (instead of an AssertionError)
  if a duplicate socket is registered.

### Fixed

- Forever was moved into `__init__` so it can be imported directly
  as aiowire.Forever.

## [1.1.0] - 2022-02-02

### Added

- See [README](README.md) for a complete description of aiowire's basic functionality.

### Fixed

- Fixed ZMQ dependency name to `pyzmq`.

[2.1.0]: https://github.com/frobnitzem/aiowire/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/frobnitzem/aiowire/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/frobnitzem/aiowire/compare/v1.0.0...v1.0.1
