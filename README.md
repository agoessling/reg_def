# Register definitions

`reg_def` parses TI target XML and generates C headers or Rust source. Both
backends use the same device model. C remains the CLI default.

## Rust generation

Load the source-generation macro from the pinned Bzlmod dependency:

```starlark
load("@reg_def//:defs.bzl", "rust_register_definition")
load("@rules_rust//rust:defs.bzl", "rust_library")

rust_register_definition(
    name = "device_registers",
    definition_file = "device.xml",
    data = [":peripheral_xml"],
    standalone = True,
)

rust_library(
    name = "registers",
    srcs = [":device_registers"],
    crate_root = ":device_registers",
)
```

This produces `device_registers.rs` with `#![no_std]`, ready to compile as a crate.
The macro emits source without requiring a particular Rust build-rule version.
The command-line equivalent is
`reg_def --language rust --standalone --ti_xml device.xml --output device_registers.rs`.

Omit `standalone` (the default) to emit definitions for `include!` inside an
existing crate instead. In that case, declare the output in `compile_data` and
provide its path through `rustc_env` for `include!(env!("DEVICE_REGISTERS"))`.

## Generated Rust API

The output supports `no_std` and Rust 2024. Register values are integer-backed
snapshots with named field getters/setters and `from_bits()` / `bits()` methods.
Single-bit fields use `bool`; other fields use the register's integer width.
Setters truncate excess high bits and preserve unrelated fields. Full-width
fields use direct assignment, avoiding redundant masks and shifts.

```rust
// Assuming the caller owns the peripheral and has enabled its clock:
unsafe {
    let mut mode = GPT0.tamr.read();
    mode.set_taild(true);
    mode.set_tamr(2);
    let timer_mode = mode.tamr(); // Extract the field, shifted down to bit zero.
    GPT0.tamr.write(mode);
}
```

### Local values and hardware access

`read()` performs a volatile hardware read and returns a local `Value` snapshot.
Field getters such as `tamr()` and setters such as `set_tamr(2)` operate only on
that snapshot. `write(value)` performs a volatile hardware write. Changing a
snapshot does not change hardware until it is explicitly written back.

Field setters are not methods on the hardware register itself. Keeping the
snapshot explicit lets a driver change several fields with one read and one
write. It also makes those accesses visible: read-modify-write is not atomic,
and it can be inappropriate for registers with read side effects or
write-one-to-clear bits. Drivers should use documented set/clear aliases where
appropriate rather than assume every register supports read-modify-write.

The snapshot is an integer-backed value, not an allocation. Accessors request
inlining; a local variable does not inherently require a stack slot. Inspect
optimized target assembly when instruction count or access order matters.

### Register-specific types

Each register definition has a distinct `Value` type, and its `write()` accepts
only that type. A value read from `GPT0.tamr` cannot be passed directly to
`GPT0.tctl.write()`, even when both registers have the same width. Copying a
snapshot or changing its fields preserves its type.

Types distinguish register definitions, not physical peripheral instances.
Instances of the same peripheral definition share their register value types,
so equivalent registers on those instances can use the same configuration.
`OtherValue::from_bits(value.bits())` explicitly converts through the underlying
integer; it bypasses this distinction and does not validate hardware semantics.

For concise raw writes, each `Value` also implements `From` for its exact
underlying integer type (`u8`, `u16`, `u32`, or `u64`). The destination register
supplies the expected value type:

```rust
// Same access requirements as any other raw register write.
unsafe { GPT0.tamr.write(2_u32.into()); }
```

This preserves every bit, exactly like `from_bits()`, without validating field
encodings. It does not convert between different registers' value types or
silently narrow wider integers. `write()` still accepts its specific `Value`,
not a generic conversion argument. Use named field setters when they explain
control bits more clearly; retain `from_bits()` for constant expressions.

### Why fields use methods

Rust has no native C-style bitfields. A field occupying a few bits has no
independent byte address, so a normal mutable pointer or reference cannot expose
just those bits. Returning a reference to the containing integer would expose
neighboring fields as well. Getters and setters implement the necessary masks
and shifts explicitly; `#[repr(packed)]` would not provide bitfield access.

### Safety boundary

`Register` and `Peripheral` describe addresses, not ownership. Raw reads and
writes are explicitly unsafe volatile operations of the XML-specified width.
Drivers remain responsible for alignment, accessible addresses, clocks, allowed
values, read/write side effects, synchronization, and exclusive peripheral use.
In particular, read-modify-write is not appropriate for every register. The
backend deliberately does not infer such behavior from XML access annotations
or produce Rust references into MMIO.

Both read and write methods are generated regardless of XML access annotations;
reserved fields can also have accessors. Their presence is not permission to use
them. Field setters enforce bit placement, not valid encodings or peripheral
state transitions. A safe application-facing driver must enforce those contracts.

### Editor hover documentation

Generated Rust doc comments expose XML descriptions on peripheral instances, register fields,
register/value types, reads/writes, and field getters/setters. Rust-analyzer displays these in
editor hover (for example, Neovim's `K`). Register documentation includes its offset and width;
field documentation includes its bit position, XML access mode, reset value, and named `bitenum`
encodings. Boolean fields show the corresponding `true`/`false` values.

Named encodings are documentation, not generated Rust enums or validation rules. XML values
outside their field width are retained and marked as such. Missing value descriptions fall back
to the XML `token` attribute. XML prose is escaped as literal Markdown text, preserving bit ranges
and comparisons in hover. The C backend and Rust register operations are unchanged.

## Validation

Bazel 7.7.1 downloads Python 3.12 and Rust 1.90.0 for the generator and tests.
Run `bazel test //test:generator_test //test:generated_test //test:type_safety_test` and
`bazel build //test:test_main //test:device_rust`. The Python regressions cover deterministic
output, widths, aliases, identifiers, invalid fields, XML named values, and attached hover docs.
Executable Rust tests
cover bit preservation, truncation, integer conversions, full-width fields,
addresses, and value sizes. Compile-fail examples verify that writes reject
other registers' values and narrowing conversions.
The existing C integration target still builds the full CC1354P10 description.
