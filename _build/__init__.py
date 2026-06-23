import os
import sys
import shutil
import pathlib
import platform
import subprocess
import zipfile
from urllib.request import urlretrieve

from setuptools.build_meta import *
from setuptools.build_meta import (
    build_editable as _build_editable,
    build_wheel as _build_wheel,
)


PEXIP_VERSION = "1.61.0-pexip1"
base_wheel_bundles = [
    {
        "wheel": "macosx_10_13_x86_64.whl",
        "machine": "x86_64",
        "platform": "darwin",
        "zip_name": "mac",
    },
    {
        "wheel": "macosx_11_0_universal2.whl",
        "machine": "x86_64",
        "platform": "darwin",
        "zip_name": "mac",
    },
    {
        "wheel": "macosx_11_0_arm64.whl",
        "machine": "arm64",
        "platform": "darwin",
        "zip_name": "mac-arm64",
    },
    {
        "wheel": "manylinux1_x86_64.whl",
        "machine": "x86_64",
        "platform": "linux",
        "zip_name": "linux",
    },
    {
        "wheel": "manylinux_2_17_aarch64.manylinux2014_aarch64.whl",
        "machine": "aarch64",
        "platform": "linux",
        "zip_name": "linux-arm64",
    },
]

SRC_ROOT = pathlib.Path(__file__).parent.parent


def _extractall(zip: zipfile.ZipFile, path: pathlib.Path) -> None:
    for name in zip.namelist():
        member = zip.getinfo(name)
        extracted_path = zip.extract(member, path)
        attr = member.external_attr >> 16
        if attr != 0:
            os.chmod(extracted_path, attr)


def _ensure_driver_bundle(zip_name: str) -> pathlib.Path:
    if os.getenv("PLAYWRIGHT_BUILD"):
        with open(SRC_ROOT / "DRIVER_SHA", "r") as fp:
            version = fp.read().strip()
    else:
        version = PEXIP_VERSION.split("-pexip")[0]
    destination_path = SRC_ROOT / "driver" / f"playwright-{version}-{zip_name}.zip"
    if destination_path.exists():
        return destination_path
    if not destination_path.parent.exists():
        destination_path.parent.mkdir()
    if os.getenv("PLAYWRIGHT_BUILD"):
        # Only build from source if PLAYWRIGHT_BUILD is set
        build_script = SRC_ROOT / "scripts" / "build_driver.sh"
        subprocess.check_call(["bash", str(build_script)])
    else:
        # Otherwise, pull binaries from GH
        url = f"https://github.com/pexip/playwright/releases/download/v{PEXIP_VERSION}/playwright-{version}-{zip_name}.zip"
        print("Downloading playwright build from:", url)
        _, headers = urlretrieve(url, destination_path)
    if not destination_path.exists():
        raise RuntimeError(
            f"Driver bundle {destination_path} is not present when it should be"
        )
    return destination_path


def _ensure_driver() -> None:
    zip_names_for_current_system = set(
        map(
            lambda wheel: wheel["zip_name"],
            filter(
                lambda wheel: wheel["machine"] == platform.machine().lower()
                              and wheel["platform"] == sys.platform,
                base_wheel_bundles,
            ),
        )
    )
    assert len(zip_names_for_current_system) == 1
    zip_name = zip_names_for_current_system.pop()
    zip_file = _ensure_driver_bundle(zip_name)
    local_driver_path = SRC_ROOT / "playwright" / "driver"
    if local_driver_path.exists():
        shutil.rmtree(local_driver_path)
    local_driver_path.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_file, "r") as zip:
        _extractall(zip, local_driver_path)
    shutil.rmtree(zip_file.parent)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    _ensure_driver()
    return _build_wheel(wheel_directory, config_settings, metadata_directory)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    _ensure_driver()
    return _build_editable(wheel_directory, config_settings, metadata_directory)
