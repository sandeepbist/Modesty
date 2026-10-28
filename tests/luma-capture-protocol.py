#!/usr/bin/env python3
"""Build the isolated protocol client without connecting to a compositor."""
import argparse
from pathlib import Path
import shlex
import subprocess


def build(output_dir):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    protocol_dir = Path(subprocess.check_output(
        ["pkg-config", "--variable=pkgdatadir", "wayland-protocols"], text=True, timeout=10
    ).strip())
    sources = []
    for name in ("ext-image-capture-source", "ext-image-copy-capture", "ext-foreign-toplevel-list"):
        stem = name + "-v1"
        xml = protocol_dir / "staging" / name / (stem + ".xml")
        header = output_dir / (stem + "-client-protocol.h")
        source = output_dir / (stem + "-protocol.c")
        for mode, target in (("client-header", header), ("private-code", source)):
            subprocess.run(["wayland-scanner", mode, str(xml), str(target)], check=True, timeout=15)
        sources.append(str(source))
    flags = shlex.split(subprocess.check_output(
        ["pkg-config", "--cflags", "--libs", "wayland-client"], text=True, timeout=10
    ))
    executable = output_dir / "session-destroy-before-capture"
    subprocess.run([
        "cc", "-std=c11", "-O2", "-g", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
        "-I", str(output_dir), str(Path(__file__).with_name("fixtures")/"luma-capture-expired-session.c"),
        *sources, *flags, "-o", str(executable),
    ], check=True, timeout=60)
    return executable


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(build(args.output_dir))
