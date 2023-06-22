load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")



def mediator_carla_deps():
    """Loads common dependencies needed to compile the protobuf library."""
    if not native.existing_rule("rules_python"):
        http_archive(
            name = "rules_python",
            sha256 = "8c15896f6686beb5c631a4459a3aa8392daccaab805ea899c9d14215074b60ef",
            strip_prefix = "rules_python-0.17.3",
            url = "https://github.com/bazelbuild/rules_python/archive/refs/tags/0.17.3.tar.gz",
        )
    if not native.existing_rule("com_github_grpc_grpc"):
        git_repository(
            name = "com_github_grpc_grpc",
            remote = "https://github.com/grpc/grpc",
            tag = "v1.45.2",
        )

    if not native.existing_rule("io_bazel_rules_docker"):
        http_archive(
            name = "io_bazel_rules_docker",
            sha256 = "b1e80761a8a8243d03ebca8845e9cc1ba6c82ce7c5179ce2b295cd36f7e394bf",
            urls = ["https://github.com/bazelbuild/rules_docker/releases/download/v0.25.0/rules_docker-v0.25.0.tar.gz"],
        )
    
    if not native.existing_rule("com_github_mvukov_rules_ros2"):
        git_repository(
            name = "com_github_mvukov_rules_ros2",
            commit = "2741dc31b6091328a9fe2300eb323f0dac48fb4a",
            remote = "https://github.com/mvukov/rules_ros2.git",
        )

    if not native.existing_rule("carla_python_api"):
        git_repository(
            name = "carla_python_api",
            commit = "e9dd91a263c070109a89ffd2a6871d2a0969b5f2",
            remote = "git@github.com:cpark90/carla_python_api.git",
        )