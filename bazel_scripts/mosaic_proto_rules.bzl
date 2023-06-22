load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")


def mosaic_proto_rules():
    """Loads common dependencies needed to compile the protobuf library."""
    if not native.existing_rule("mosaic_proto"):
        git_repository(
            name = "mosaic_proto",
            remote = "https://github.com/cpark90/mosaic_proto",
            tag = "v0.01",
        )