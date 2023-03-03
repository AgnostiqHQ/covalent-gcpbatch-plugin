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

import pytest
from unittest.mock import MagicMock, AsyncMock
from covalent_gcpbatch_plugin import GCPBatchExecutor


@pytest.fixture
def gcpbatch_executor():
    return GCPBatchExecutor(
        project_id="test-project",
        bucket_name="test-bucket",
        container_image_uri="test-container",
        service_account_email="test-email",
        region="test-region",
        vcpus=2,
        memory=256,
        time_limit=300,
        poll_freq=2,
        retries=1,
    )


def test_executor_explicit_constructor(mocker):
    """
    Test that init is properly called when all attributes are passed in directly. Ensure that get_config is not invoked
    """
    mock_get_config = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.get_config")
    test_executor = GCPBatchExecutor(
        project_id="test-project",
        bucket_name="test-bucket",
        container_image_uri="test-container",
        service_account_email="test-email",
        region="test-region",
        vcpus=2,
        memory=256,
        time_limit=300,
        poll_freq=2,
        retries=1,
    )

    assert test_executor.project_id == "test-project"
    assert test_executor.bucket_name == "test-bucket"
    assert test_executor.container_image_uri == "test-container"
    assert test_executor.service_account_email == "test-email"
    assert test_executor.region == "test-region"
    assert test_executor.vcpus == 2
    assert test_executor.memory == 256
    assert test_executor.time_limit == 300
    assert test_executor.poll_freq == 2
    assert test_executor.retries == 1
    assert mock_get_config.call_count == 0


def test_executor_default_constructor(mocker):
    """
    Test that all executor configuration values are read via invoking get_config
    """
    mock_get_config = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.get_config")
    GCPBatchExecutor()
    assert mock_get_config.call_count == 10
