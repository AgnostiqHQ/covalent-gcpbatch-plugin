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

ARG COVALENT_BASE_IMAGE=python:3.8-slim-buster
FROM ${COVALENT_BASE_IMAGE}

# Install dependencies
ARG COVALENT_TASK_ROOT=/usr/src

ARG COVALENT_PACKAGE_VERSION

# Not used anymore for now
ARG PRE_RELEASE

COPY requirements-image.txt requirements.txt
RUN apt-get update && pip install -r requirements.txt

# Commenting this out for now as we switch to specifying the package version directly
# RUN if [ -z "$PRE_RELEASE" ]; then \
# 		pip install "$COVALENT_PACKAGE_VERSION"; else \
# 		pip install --pre "$COVALENT_PACKAGE_VERSION"; \
# 	fi

RUN if [ -z "$COVALENT_PACKAGE_VERSION" ]; then \
		pip install covalent; else \
		pip install "covalent==$COVALENT_PACKAGE_VERSION"; \
	fi

# Making sure the right version of cloudpickle is installed after covalent
RUN pip install "cloudpickle>2, <3"


COPY exec.py ${COVALENT_TASK_ROOT}

WORKDIR ${COVALENT_TASK_ROOT}
ENV PYTHONPATH ${COVALENT_TASK_ROOT}:${PYTHONPATH}

# Path where the storage bucket will be mounted inside the container
ENV GCPBATCH_TASK_MOUNTPOINT /mnt/disks/covalent

ENTRYPOINT [ "python", "exec.py" ]
