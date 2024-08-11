load("//:defs.bzl", "register_definition")

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
