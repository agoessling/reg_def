py_binary(
    name = "reg_def",
    srcs = ["reg_def.py"],
    visibility = ["//visibility:public"],
    deps = [
        ":c_generator",
        ":ti_parser",
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
