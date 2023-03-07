# Copyright 2023 Agnostiq Inc.
#
# This file is part of Covalent.
#
# Licensed under the GNU Affero General Public License 3.0 (the "License").
# A copy of the License may be obtained with this software package or at
#
#      https://www.gnu.org/licenses/agpl-3.0.en.html
#
# Use of this file is prohibited except in compliance with the License. Any
# modifications or derivative works of this file must retain this copyright
# notice, and modified files must contain a notice indicating that they have
# been altered from the originals.
#
# Covalent is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the License for more details.
#
# Relief from the License may be granted by purchasing a commercial license.

ARG COVALENT_BASE_IMAGE=python:3.8-slim-buster
FROM ${COVALENT_BASE_IMAGE}

# Install dependencies
ARG COVALENT_TASK_ROOT=/usr/src
ARG COVALENT_PACKAGE_VERSION
ARG PRE_RELEASE

RUN apt-get update && \
		pip install 'google-cloud-batch==0.9.0' 'google-cloud-storage==2.7.0'


RUN if [ -z "$PRE_RELEASE" ]; then \
		pip install "$COVALENT_PACKAGE_VERSION"; else \
		pip install --pre "$COVALENT_PACKAGE_VERSION"; \
	fi


COPY covalent_gcpbatch_plugin/exec.py ${COVALENT_TASK_ROOT}

WORKDIR ${COVALENT_TASK_ROOT}
ENV PYTHONPATH ${COVALENT_TASK_ROOT}:${PYTHONPATH}

# Path where the storage bucket will be mounted inside the container
ENV GCPBATCH_TASK_MOUNTPOINT /mnt/disks/covalent

ENTRYPOINT [ "python", "exec.py" ]
