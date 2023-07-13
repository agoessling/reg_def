workspace(name = "reg_def")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

# bazel_lint
http_archive(
    name = "bazel_lint",
    sha256 = "85b8cab2998fc7ce32294d6473276ba70eea06b0eef4bce47de5e45499e7096f",
    strip_prefix = "bazel_lint-0.1.1",
    url = "https://github.com/agoessling/bazel_lint/archive/v0.1.1.zip",
)

load("@bazel_lint//bazel_lint:bazel_lint_first_level_deps.bzl", "bazel_lint_first_level_deps")

bazel_lint_first_level_deps()

load("@bazel_lint//bazel_lint:bazel_lint_second_level_deps.bzl", "bazel_lint_second_level_deps")

bazel_lint_second_level_deps()
