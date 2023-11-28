# Copyright 2023 Agnostiq Inc.
#
# This file is part of Covalent.
#
# Licensed under the Apache License 2.0 (the "License"). A copy of the
# License may be obtained with this software package or at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Use of this file is prohibited except in compliance with the License.
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import shutil
import site
import sys
from pathlib import Path

from setuptools import find_packages, setup

site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

# When updating, VERSION should be set to that of the latest
# covalent-gcpbatch-plugin (ie, this package).
with open("VERSION", "r", encoding="utf-8") as f:
    version = f.read().strip()

with open("requirements.txt", "r", encoding="utf-8") as f:
    required = f.read().splitlines()

PACKAGE_NAME = "covalent_gcpbatch_plugin"
PLUGINS_LIST = [f"gcpbatch = {PACKAGE_NAME}.gcpbatch"]

setup_info = {
    "name": "covalent-gcpbatch-plugin",
    "packages": find_packages("."),
    "version": version,
    "maintainer": "Agnostiq",
    "url": "https://github.com/AgnostiqHQ/covalent-gcpbatch-plugin",
    "download_url": f"https://github.com/AgnostiqHQ/covalent-gcpbatch-plugin/archive/v{version}.tar.gz",
    "license": "Apache License 2.0",
    "author": "Agnostiq",
    "author_email": "support@agnostiq.ai",
    "description": "Covalent GCP Batch Plugin",
    "long_description": open("README.md", "r", encoding="utf-8").read(),
    "long_description_content_type": "text/markdown",
    "include_package_data": True,
    "install_requires": required,
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Plugins",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Adaptive Technologies",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator",
        "Topic :: Software Development",
        "Topic :: System :: Distributed Computing",
    ],
    "entry_points": {
        "covalent.executor.executor_plugins": PLUGINS_LIST,
    },
}


def _create_docker_subdir() -> Path:
    """
    Create a dir with files for docker image build from site-packages.
    """
    base_dir = Path(".").absolute()
    docker_dir = base_dir / f"{PACKAGE_NAME}/assets/infra/docker"

    dummy_dir = docker_dir / PACKAGE_NAME
    dummy_dir.mkdir(exist_ok=True, parents=True)

    for file in [
        base_dir / "Dockerfile",
        base_dir / "requirements.txt",
        base_dir / f"{PACKAGE_NAME}/exec.py",
    ]:
        shutil.copy(file, docker_dir)

    return docker_dir


def main():
    """Install entry-point."""
    _docker_dir = None

    if "-e" not in sys.argv:
        # Non-editable install needs to include files to build docker image.
        _docker_dir = _create_docker_subdir()
        setup_info.update(package_data={PACKAGE_NAME: ["assets/infra/docker/*"]})

    setup(**setup_info)

    if _docker_dir is not None:
        # Clean up sub-dir created for non-editable install.
        shutil.rmtree(_docker_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
