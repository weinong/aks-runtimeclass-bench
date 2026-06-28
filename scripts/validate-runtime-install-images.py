#!/usr/bin/env python3
import subprocess
from pathlib import Path


EXPECTED_INSTALLER_IMAGE = "mcr.microsoft.com/azurelinux/busybox:1.36"
EXPECTED_PYTHON_IMAGE = "mcr.microsoft.com/azurelinux/base/python:3"
RUNTIME_INSTALL_DIR = Path("configs/runtime-install")


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def validate_embedded_shell(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "- |":
            continue
        indent = len(line) - len(line.lstrip())
        script_lines = []
        for script_line in lines[index + 1 :]:
            if not script_line.strip():
                script_lines.append("")
                continue
            script_indent = len(script_line) - len(script_line.lstrip())
            if script_indent <= indent:
                break
            script_lines.append(script_line[indent + 2 :])
        if script_lines:
            subprocess.run(["/bin/sh", "-n"], input="\n".join(script_lines), text=True, check=True)


def main():
    require(RUNTIME_INSTALL_DIR.is_dir(), f"missing directory: {RUNTIME_INSTALL_DIR}")

    files = sorted(RUNTIME_INSTALL_DIR.rglob("*.yaml"))
    require(files, f"missing runtime install manifests under {RUNTIME_INSTALL_DIR}")
    manifest_text = "\n".join(path.read_text(encoding="utf-8") for path in files)
    for path in files:
        validate_embedded_shell(path)

    banned_images = ["ubuntu:", "python:3.12-slim", "python-slim"]
    for banned_image in banned_images:
        require(banned_image not in manifest_text, f"runtime install manifests must not reference {banned_image}")

    banned_commands = ["apt-get", "wget -q", "\n              nsenter --target"]
    for banned_command in banned_commands:
        require(banned_command not in manifest_text, f"runtime install manifests must not use {banned_command}")

    require(
        manifest_text.count(f"image: {EXPECTED_INSTALLER_IMAGE}") == 2,
        f"gVisor and Firecracker installers must use {EXPECTED_INSTALLER_IMAGE}",
    )
    require(
        manifest_text.count(f"image: {EXPECTED_PYTHON_IMAGE}") == 2,
        f"gVisor and Firecracker smoke pods must use {EXPECTED_PYTHON_IMAGE}",
    )
    require(
        manifest_text.count("chroot /host /usr/bin/nsenter") == 2,
        "installer manifests must run host mutations through host nsenter from the mounted node root",
    )


if __name__ == "__main__":
    main()
