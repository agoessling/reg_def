load("@bazel_lint//bazel:buildifier.bzl", "buildifier")

# load("@bazel_lint//cpp:clang.bzl", "clang_format")
load("@bazel_lint//python:pylint.bzl", "pylint")
load("@bazel_lint//python:yapf.bzl", "yapf")

buildifier(
    name = "format_bazel",
    srcs = ["WORKSPACE"],
    glob = [
        "**/*BUILD",
        "**/*.bzl",
    ],
    glob_exclude = [
        "bazel-*/**",
    ],
)

# clang_format(
#     name = "format_cc",
#     glob = [
#         "**/*.c",
#         "**/*.cc",
#         "**/*.h",
#     ],
#     glob_exclude = [
#         "bazel-*/**",
#         "third_party/**",
#     ],
#     style_file = ".clang-format",
# )

yapf(
    name = "format_python",
    glob = [
        "**/*.py",
    ],
    glob_exclude = [
        "bazel-*/**",
        "third_party/**",
    ],
    style_file = ".style.yapf",
)

pylint(
    name = "lint_python",
    glob = [
        "**/*.py",
    ],
    glob_exclude = [
        "bazel-*/**",
        "third_party/**",
    ],
    rcfile = "pylintrc",
)

py_binary(
    name = "reg_def",
    srcs = ["reg_def.py"],
    visibility = ["//visibility:public"],
    deps = [":ti_parser"],
)

py_library(
    name = "ti_parser",
    srcs = ["ti_parser.py"],
    deps = [":device_types"],
)

py_library(
    name = "device_types",
    srcs = ["device_types.py"],
)
