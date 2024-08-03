py_binary(
    name = "reg_def",
    srcs = ["reg_def.py"],
    visibility = ["//visibility:public"],
    deps = [
        ":ti_parser",
        ":c_generator",
    ],
)

py_library(
    name = "ti_parser",
    srcs = ["ti_parser.py"],
    deps = [":device_types"],
)

py_library(
    name = "c_generator",
    srcs = ["c_generator.py"],
    deps = [":device_types"],
)

py_library(
    name = "device_types",
    srcs = ["device_types.py"],
)

genrule(
    name = "gen_test_header",
    tools = [":reg_def"],
    outs = ["test_header.h"],
    cmd = "$(location :reg_def) --definition /home/agoessling/ti/ccs1271/ccs/ccs_base/common/targetdb/devices/cc1354p10.xml --output $@",
)

cc_library(
   name = "test_header",
   hdrs = ["test_header.h"],
)

cc_binary(
   name = "test_main",
   srcs = ["test_main.c"],
   deps = [":test_header"],
)

# BEGIN ==================== lint_it_all ====================
exports_files([
    ".clang-tidy",
    ".ruff.toml",
])

alias(
    name = "format",
    actual = "//tools/format",
)
# END ==================== lint_it_all ====================
