# Register definitions

`reg_def` parses TI target XML and generates C headers or Rust source. Both
backends use the same device model. C remains the CLI default.

## Rust generation

Load the source-generation macro from the pinned Bzlmod dependency:

```starlark
load("@reg_def//:defs.bzl", "rust_register_definition")

rust_register_definition(
    name = "device_registers",
    definition_file = "device.xml",
    data = [":peripheral_xml"],
)
```

This produces `device_registers.rs`. In the consuming `rust_library`, put the
source target in `compile_data`, set a `rustc_env` entry to
`"$(execpath :device_registers)"`, and use `include!(env!("DEVICE_REGISTERS"))`.
The macro emits source rather than imposing a Rust crate structure or a Rust
build-rule version on consumers. The command-line equivalent is
`reg_def --language rust --ti_xml device.xml --output device_registers.rs`.

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
    GPT0.tamr.write(mode);
}
```

`Register` and `Peripheral` describe addresses, not ownership. Raw reads and
writes are explicitly unsafe volatile operations of the XML-specified width.
Drivers remain responsible for alignment, accessible addresses, clocks, allowed
values, read/write side effects, synchronization, and exclusive peripheral use.
In particular, read-modify-write is not appropriate for every register. The
backend deliberately does not infer such behavior from XML access annotations
or produce Rust references into MMIO.

## Validation

Bazel 7.7.1 downloads Python 3.12 and Rust 1.90.0 for the generator and tests.
Run `bazel test //test:generator_test //test:generated_test` and
`bazel build //test:test_main //test:device_rust`. The Python regressions cover deterministic
output, widths, aliases, identifiers, and invalid fields. Executable Rust tests
cover bit preservation, truncation, full-width fields, addresses, and value sizes.
The existing C integration target still builds the full CC1354P10 description.
