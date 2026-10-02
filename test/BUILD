load("@rules_python//python:defs.bzl", "py_binary", "py_test")
load("@rules_rust//rust:defs.bzl", "rust_library", "rust_test")
load("//:defs.bzl", "register_definition", "rust_register_definition")

register_definition(
    name = "test_header",
    out = "test_header.h",
    data = ["//third_party/ti/targetdb:all_files"],
    definition_file = "//third_party/ti/targetdb:devices/cc1354p10.xml",
    definition_type = "ti",
)

cc_binary(
    name = "test_main",
    srcs = ["test_main.c"],
    deps = [":test_header"],
)

py_test(
    name = "generator_test",
    size = "small",
    srcs = ["generator_test.py"],
    deps = [
        "//src:device_types",
        "//src:rust_generator",
    ],
)

py_binary(
    name = "fixture_generator",
    srcs = ["fixture.py"],
    main = "fixture.py",
    deps = [
        "//src:device_types",
        "//src:rust_generator",
    ],
)

genrule(
    name = "fixture",
    outs = ["fixture.rs"],
    cmd = "$(execpath :fixture_generator) $@",
    tools = [":fixture_generator"],
)

rust_test(
    name = "generated_test",
    size = "small",
    srcs = ["generated_test.rs"],
    compile_data = [":fixture"],
    crate_root = "generated_test.rs",
    edition = "2024",
    rustc_env = {"REGISTER_FIXTURE": "$(execpath :fixture)"},
)

rust_register_definition(
    name = "device_registers",
    data = ["//third_party/ti/targetdb:all_files"],
    definition_file = "//third_party/ti/targetdb:devices/cc1354p10.xml",
)

rust_library(
    name = "device_rust",
    srcs = ["device.rs"],
    compile_data = [":device_registers"],
    crate_root = "device.rs",
    edition = "2024",
    rustc_env = {"DEVICE_REGISTERS": "$(execpath :device_registers)"},
)
