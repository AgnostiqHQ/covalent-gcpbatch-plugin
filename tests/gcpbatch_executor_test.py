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

from google.cloud.batch_v1.services.batch_service.async_client import service_account
import pytest
import os
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
        cache_dir="/tmp",
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
        cache_dir="/tmp",
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
    assert test_executor.cache_dir == "/tmp"
    assert mock_get_config.call_count == 0


def test_executor_default_constructor(mocker):
    """
    Test that all executor configuration values are read via invoking get_config
    """
    mock_get_config = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.get_config")
    GCPBatchExecutor()
    assert mock_get_config.call_count == 10


@pytest.mark.asyncio
async def test_pickle_function(gcpbatch_executor, mocker):
    """
    Test executor properly pickles the function
    """

    def f(x):
        return x

    mock_app_log = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.app_log.debug")
    dispatch_id = "abcdef"
    node_id = 0
    task_metadata = {"dispatch_id": dispatch_id, "node_id": node_id}
    mock_pickle_dump = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.pickle.dump")

    await gcpbatch_executor._pickle_func(f, 1, {}, task_metadata)

    assert mock_app_log.call_count == 2
    mock_pickle_dump.assert_called_once()


@pytest.mark.asyncio
async def test_upload_task(gcpbatch_executor, mocker):
    """Test the executor uploads the pickled object properly to the bucket"""
    func_filename = "test.pkl"

    mock_app_log = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.app_log.debug")
    mock_storage_client = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.storage.Client", return_value=MagicMock()
    )

    await gcpbatch_executor._upload_task(func_filename)

    mock_app_log.assert_called_once()
    mock_storage_client.assert_called_once()
    mock_storage_client.return_value.bucket.assert_called_once_with(gcpbatch_executor.bucket_name)
    mock_storage_client.return_value.bucket.return_value.blob.assert_called_once_with(
        func_filename
    )


@pytest.mark.asyncio
async def test_create_batch_job(gcpbatch_executor, mocker):
    """Test batch job create"""
    dispatch_id = "abcdef"
    node_id = 0
    task_metadata = {"dispatch_id": dispatch_id, "node_id": node_id}
    image_uri = "test-image"

    func_filename = f"func-{dispatch_id}-{node_id}.pkl"
    result_filename = f"result-{dispatch_id}-{node_id}.pkl"
    exception_filename = f"exception-{dispatch_id}-{node_id}.json"

    mock_app_log_debug = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.app_log.debug")
    mock_batch_v1 = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.batch_v1")
    mock_task_spec = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.batch_v1.TaskSpec", return_value=MagicMock()
    )
    mock_runnable = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.batch_v1.Runnable", return_value=MagicMock()
    )

    await gcpbatch_executor._create_batch_job(image_uri, task_metadata)
    mock_task_spec.assert_called_once()
    mock_runnable.assert_called_once()
    mock_batch_v1.Runnable.Container.assert_called_once_with(image_uri=image_uri)
    mock_task_spec.return_value.runnables.append.assert_called_once_with(
        mock_runnable.return_value
    )
    mock_batch_v1.Environment.assert_called_once_with(
        variables={
            "COVALENT_TASK_FUNC_FILENAME": os.path.join("/mnt/disks/covalent", func_filename),
            "RESULT_FILENAME": os.path.join("/mnt/disks/covalent", result_filename),
            "EXCEPTION_FILENAME": os.path.join("/mnt/disks/covalent", exception_filename),
        }
    )
    mock_batch_v1.GCS.assert_called_once()
    assert mock_batch_v1.GCS.return_value.remote_path == gcpbatch_executor.bucket_name
    mock_batch_v1.Volume.assert_called_once()
    assert mock_batch_v1.Volume.return_value.gcs == mock_batch_v1.GCS.return_value
    assert mock_batch_v1.Volume.return_value.mount_path == "/mnt/disks/covalent"
    assert mock_batch_v1.TaskSpec.return_value.volumes == [mock_batch_v1.Volume.return_value]

    mock_batch_v1.ComputeResource.assert_called_once_with(
        cpu_milli=gcpbatch_executor.vcpus * 1000, memory_mib=gcpbatch_executor.memory
    )

    assert mock_batch_v1.TaskSpec.return_value.compute_resource == mock_batch_v1.ComputeResource(
        cpu_milli=gcpbatch_executor.vcpus * 1000, memory_mib=gcpbatch_executor.memory
    )
    assert mock_batch_v1.TaskSpec.return_value.max_retry_count == gcpbatch_executor.retries
    assert (
        mock_batch_v1.TaskSpec.return_value.max_run_duration == f"{gcpbatch_executor.time_limit}s"
    )

    mock_batch_v1.TaskGroup.assert_called_once_with(
        task_count=1, task_spec=mock_batch_v1.TaskSpec.return_value
    )
    mock_batch_v1.AllocationPolicy.assert_called_once_with(
        service_account={"email": gcpbatch_executor.service_account_email}
    )
    mock_batch_v1.LogsPolicy.assert_called_once_with(destination="CLOUD_LOGGING")
    mock_batch_v1.Job.assert_called_once_with(
        task_groups=[mock_batch_v1.TaskGroup.return_value],
        allocation_policy=mock_batch_v1.AllocationPolicy.return_value,
        logs_policy=mock_batch_v1.LogsPolicy.return_value,
    )
