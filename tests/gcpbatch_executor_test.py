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

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from covalent._shared_files.exceptions import TaskCancelledError
from google.cloud.batch_v1.services.batch_service.async_client import service_account

from covalent_gcpbatch_plugin import GCPBatchExecutor, gcpbatch


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
    assert mock_get_config.call_count == 11


def test_get_batch_service_client(gcpbatch_executor, mocker):
    """Test batch service client async"""
    mock_batch_v1 = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.batch_v1")
    gcpbatch_executor._get_batch_client()
    mock_batch_v1.BatchServiceAsyncClient.assert_called_once()


def test_validate_credentials(gcpbatch_executor, mocker):
    """Test credential validation for gcloud"""
    assert gcpbatch_executor._validate_credentials()


@pytest.mark.asyncio
async def test_executor_run(gcpbatch_executor, mocker):
    """Test executor run"""
    mock_function = MagicMock()
    mock_args = MagicMock()
    mock_kwargs = MagicMock()

    dispatch_id = "abcdef"
    node_id = 0
    mock_task_metadata = {"dispatch_id": dispatch_id, "node_id": node_id}
    mock_batch_job_name = "mock-batch-job"
    mock_result_filename = "mock-result.pkl"
    mock_exception_filename = "mock-exception.json"

    mock_local_func_filename = "/tmp/func.pkl"

    gcpbatch_executor._debug_log = MagicMock()
    gcpbatch_executor._upload_task = AsyncMock()
    gcpbatch_executor.get_cancel_requested = AsyncMock(return_value=False)
    gcpbatch_executor._pickle_func = AsyncMock(return_value=mock_local_func_filename)
    gcpbatch_executor._create_batch_job = AsyncMock()
    gcpbatch_executor.submit_task = AsyncMock()
    gcpbatch_executor.set_job_handle = AsyncMock()
    gcpbatch_executor._poll_task = AsyncMock(return_value=mock_result_filename)

    await gcpbatch_executor.run(mock_function, mock_args, mock_kwargs, mock_task_metadata)

    gcpbatch_executor._debug_log.assert_called()
    gcpbatch_executor._upload_task.assert_awaited()
    gcpbatch_executor.get_cancel_requested.assert_awaited()
    gcpbatch_executor._pickle_func.assert_awaited()
    gcpbatch_executor._create_batch_job.assert_awaited()
    gcpbatch_executor.submit_task.assert_awaited()
    gcpbatch_executor.set_job_handle.assert_awaited()
    gcpbatch_executor._poll_task.assert_awaited()


@pytest.mark.asyncio
async def test_executor_run_task_cancelled_when_pickling_func(gcpbatch_executor, mocker):
    """Test task cancelled error is raised when pickling the function"""
    mock_function = MagicMock()
    mock_args = MagicMock()
    mock_kwargs = MagicMock()

    dispatch_id = "abcdef"
    node_id = 0
    mock_task_metadata = {"dispatch_id": dispatch_id, "node_id": node_id}
    mock_batch_job_name = "mock-batch-job"
    mock_result_filename = "mock-result.pkl"
    mock_exception_filename = "mock-exception.json"

    mock_local_func_filename = "/tmp/func.pkl"

    gcpbatch_executor._debug_log = MagicMock()
    gcpbatch_executor._upload_task = AsyncMock()
    gcpbatch_executor.get_cancel_requested = AsyncMock(return_value=True)

    with pytest.raises(TaskCancelledError):
        await gcpbatch_executor.run(mock_function, mock_args, mock_kwargs, mock_task_metadata)

    gcpbatch_executor._debug_log.assert_called_once_with("TASK CANCELLED")


@pytest.mark.asyncio
async def test_upload_task_exception_handling(gcpbatch_executor, mocker):
    """Test exception handling when uploading task to bucket"""
    mock_func_filename = "func.pkl"
    mock_app_log_exception = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.app_log.exception")
    mock_storage_client = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.storage.Client", return_value=MagicMock()
    )

    mock_blob = mock_storage_client.return_value.bucket.return_value.blob.return_value
    mock_blob.upload_from_filename = MagicMock(side_effect=Exception("error"))

    with pytest.raises(Exception):
        await gcpbatch_executor._upload_task(mock_func_filename)

    mock_storage_client.assert_called_once()
    mock_storage_client.return_value.bucket.assert_called_once_with(gcpbatch_executor.bucket_name)
    mock_storage_client.return_value.bucket.return_value.blob.assert_called_once_with(
        mock_func_filename
    )
    mock_app_log_exception.assert_called_once_with(
        f"Failed to upload func.pkl to {gcpbatch_executor.bucket_name}"
    )


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
            "COVALENT_TASK_FUNC_FILENAME": func_filename,
            "RESULT_FILENAME": result_filename,
            "EXCEPTION_FILENAME": exception_filename,
            "COVALENT_BUCKET_NAME": gcpbatch_executor.bucket_name,
        }
    )

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


@pytest.mark.asyncio
async def test_submit_task(gcpbatch_executor, mocker):
    """Test task submission"""
    mock_batch_job = MagicMock()
    dispatch_id = "abcdef"
    node_id = 0
    mock_get_batch_service_client = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.GCPBatchExecutor._get_batch_client",
        return_value=AsyncMock(),
    )
    mock_batch_v1 = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.batch_v1")

    await gcpbatch_executor.submit_task(
        dispatch_id=dispatch_id, node_id=node_id, batch_job=mock_batch_job
    )

    mock_batch_v1.CreateJobRequest.assert_called_once()
    assert mock_batch_v1.CreateJobRequest.return_value.job == mock_batch_job
    assert mock_batch_v1.CreateJobRequest.return_value.job_id == f"job-{dispatch_id}-{node_id}"
    assert (
        mock_batch_v1.CreateJobRequest.return_value.parent
        == f"projects/{gcpbatch_executor.project_id}/locations/{gcpbatch_executor.region}"
    )

    mock_get_batch_service_client.return_value.create_job.assert_awaited_once_with(
        mock_batch_v1.CreateJobRequest.return_value
    )


@pytest.mark.asyncio
async def test_get_job_state(gcpbatch_executor, mocker):
    """Test getting batch job state"""
    mock_job_name = "test_job"
    mock_get_batch_client = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.GCPBatchExecutor._get_batch_client",
        return_value=AsyncMock(),
    )
    await gcpbatch_executor.get_job_state(mock_job_name)

    mock_get_batch_client.assert_called_once()
    mock_get_batch_client.return_value.get_job.assert_awaited_once_with(
        name=f"projects/{gcpbatch_executor.project_id}/locations/{gcpbatch_executor.region}/jobs/{mock_job_name}"
    )


@pytest.mark.asyncio
async def test_get_status_true(gcpbatch_executor, mocker):
    """Testing querying status of the job"""
    mock_object_key = "test"
    mock_blob = MagicMock()
    mock_blob.name = "test"
    mock_storage_client = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.storage.Client", return_value=MagicMock()
    )
    mock_storage_client.return_value.list_blobs.return_value = [mock_blob]

    res = await gcpbatch_executor.get_status(object_key=mock_object_key)

    mock_storage_client.assert_called_once()
    mock_storage_client.return_value.list_blobs.assert_called_once_with(
        gcpbatch_executor.bucket_name
    )
    assert res


@pytest.mark.asyncio
async def test_get_status_false(gcpbatch_executor, mocker):
    """Testing querying status of the job"""
    mock_object_key = "test2"
    mock_blob = MagicMock()
    mock_blob.name = "test"
    mock_storage_client = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.storage.Client", return_value=MagicMock()
    )
    mock_storage_client.return_value.list_blobs.return_value = [mock_blob]

    res = await gcpbatch_executor.get_status(object_key=mock_object_key)

    mock_storage_client.assert_called_once()
    mock_storage_client.return_value.list_blobs.assert_called_once_with(
        gcpbatch_executor.bucket_name
    )
    assert not res


@pytest.mark.asyncio
async def test_poll_task_raises_exception(gcpbatch_executor, mocker):
    """Test polling for result/exception object"""
    dispatch_id = "abcdef"
    node_id = 0
    task_metadata = {"dispatch_id": dispatch_id, "node_id": node_id}
    mock_result_filename = "result.pkl"
    mock_exception_filename = "exception.json"

    gcpbatch_executor.time_limit = -1
    with pytest.raises(TimeoutError):
        await gcpbatch_executor._poll_task(
            task_metadata, mock_result_filename, mock_exception_filename
        )


@pytest.mark.asyncio
async def test_poll_task_deletion_in_progress(gcpbatch_executor, mocker):
    """Test poll task functionality"""
    dispatch_id = "abcdef"
    node_id = 0
    task_metadata = {"dispatch_id": dispatch_id, "node_id": node_id}
    gcpbatch_executor.time_limit = 2
    gcpbatch_executor.poll_freq = 2
    gcpbatch_executor.get_job_state = AsyncMock(return_value="DELETION_IN_PROGRESS")
    gcpbatch_executor.get_cancel_requested = AsyncMock(return_value=True)

    with pytest.raises(TaskCancelledError):
        await gcpbatch_executor._poll_task(task_metadata, "result.pkl", "exception.pkl")


@pytest.mark.asyncio
async def test_poll_task_succeeded(gcpbatch_executor, mocker):
    """Test poll task functionality"""
    dispatch_id = "abcdef"
    node_id = 0
    task_metadata = {"dispatch_id": dispatch_id, "node_id": node_id}
    job_name = f"job-{dispatch_id}-{node_id}"
    result_filename = f"result-{dispatch_id}-{node_id}.pkl"
    exception_filename = f"result-{dispatch_id}-{node_id}.pkl"
    gcpbatch_executor.time_limit = 2
    gcpbatch_executor.poll_freq = 2
    gcpbatch_executor.get_job_state = AsyncMock(return_value="SUCCEEDED")
    mock_app_log_debug = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.GCPBatchExecutor._debug_log"
    )
    gcpbatch_executor.get_status = AsyncMock(return_value=True)

    res = await gcpbatch_executor._poll_task(task_metadata, result_filename, exception_filename)

    assert mock_app_log_debug.call_count == 2
    gcpbatch_executor.get_job_state.assert_awaited_once_with(job_name)
    gcpbatch_executor.get_status.assert_awaited_once_with(result_filename)
    assert res == result_filename


@pytest.mark.asyncio
async def test_poll_task_failed(gcpbatch_executor, mocker):
    """Test polling task when batch job failed"""
    dispatch_id = "abcdef"
    node_id = 0
    task_metadata = {"dispatch_id": dispatch_id, "node_id": node_id}
    job_name = f"job-{dispatch_id}-{node_id}"
    result_filename = f"result-{dispatch_id}-{node_id}.pkl"
    exception_filename = f"result-{dispatch_id}-{node_id}.pkl"

    gcpbatch_executor.time_limit = 2
    gcpbatch_executor.poll_freq = 2

    gcpbatch_executor.get_job_state = AsyncMock(return_value="FAILED")
    mock_app_log_debug = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.GCPBatchExecutor._debug_log"
    )
    gcpbatch_executor.get_status = AsyncMock(return_value=True)

    res = await gcpbatch_executor._poll_task(task_metadata, result_filename, exception_filename)

    assert mock_app_log_debug.call_count == 2
    gcpbatch_executor.get_job_state.assert_awaited_once_with(job_name)
    gcpbatch_executor.get_status.assert_awaited_once_with(exception_filename)
    assert res == exception_filename


@pytest.mark.asyncio
async def test_poll_task_state_unspecified(gcpbatch_executor, mocker):
    """Test polling task for state unspecified task"""
    dispatch_id = "abcdef"
    node_id = 0
    task_metadata = {"dispatch_id": dispatch_id, "node_id": node_id}
    job_name = f"job-{dispatch_id}-{node_id}"
    result_filename = f"result-{dispatch_id}-{node_id}.pkl"
    exception_filename = f"result-{dispatch_id}-{node_id}.pkl"

    gcpbatch_executor.time_limit = 2
    gcpbatch_executor.poll_freq = 2

    gcpbatch_executor.get_job_state = AsyncMock(return_value="STATE_UNSPECIFIED")
    mock_app_log_debug = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.GCPBatchExecutor._debug_log"
    )
    gcpbatch_executor.get_status = AsyncMock(return_value=True)

    with pytest.raises(RuntimeError):
        await gcpbatch_executor._poll_task(task_metadata, result_filename, exception_filename)

    assert mock_app_log_debug.call_count == 1
    gcpbatch_executor.get_job_state.assert_awaited_once_with(job_name)


@pytest.mark.asyncio
async def test_poll_task_not_listed_state(gcpbatch_executor, mocker):
    """Test polling sleeping when not state matches"""
    dispatch_id = "abcdef"
    node_id = 0
    task_metadata = {"dispatch_id": dispatch_id, "node_id": node_id}
    result_filename = f"result-{dispatch_id}-{node_id}.pkl"
    exception_filename = f"result-{dispatch_id}-{node_id}.pkl"

    gcpbatch_executor.time_limit = 2
    gcpbatch_executor.poll_freq = 2

    gcpbatch_executor.get_job_state = AsyncMock(return_value="STATE_UNKNOWN")
    mock_app_log_debug = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.GCPBatchExecutor._debug_log"
    )
    mock_asyncio_sleep = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.asyncio.sleep")
    gcpbatch_executor.get_status = AsyncMock(return_value=True)

    with pytest.raises(TimeoutError):
        await gcpbatch_executor._poll_task(task_metadata, result_filename, exception_filename)

    assert mock_app_log_debug.call_count == 1
    mock_asyncio_sleep.assert_awaited_once_with(gcpbatch_executor.poll_freq)


@pytest.mark.asyncio
async def test_download_blob_to_file_no_exception(gcpbatch_executor, mocker):
    """Test downloading blob from bucket to file"""
    local_blob_filename = "/tmp/blob"
    mock_os_path_join = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.os.path.join", return_value=local_blob_filename
    )
    mock_storage_client = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.storage.Client", return_value=MagicMock()
    )

    await gcpbatch_executor._download_blob_to_file(gcpbatch_executor.bucket_name, "blob")

    mock_os_path_join.assert_called_once_with(gcpbatch_executor.cache_dir, "blob")
    mock_storage_client.assert_called()
    mock_storage_client.return_value.bucket.assert_called_once_with(gcpbatch_executor.bucket_name)
    mock_storage_client.return_value.bucket.return_value.blob.assert_called_once_with("blob")
    mock_storage_client.return_value.bucket.return_value.blob.return_value.download_to_filename.assert_called_once_with(
        local_blob_filename
    )


@pytest.mark.asyncio
async def test_download_blob_to_file_exception(gcpbatch_executor, mocker):
    """Test exception handling when its raised when downloading the blob from bucket"""
    mock_app_log_debug = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.GCPBatchExecutor._debug_log"
    )
    mock_os_path_join = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.os.path.join", return_value="/tmp/blob"
    )
    mock_storage_client = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.storage.Client", side_effect=Exception("error")
    )

    with pytest.raises(Exception) as ex:
        await gcpbatch_executor._download_blob_to_file(gcpbatch_executor.bucket_name, "blob")

    mock_app_log_debug.assert_called_once()
    mock_os_path_join.assert_called_once_with(gcpbatch_executor.cache_dir, "blob")
    mock_storage_client.assert_called_once()


@pytest.mark.asyncio
async def test_query_task_exception_raising_exception(gcpbatch_executor, mocker):
    """Test exception handling when querying task exception"""
    exception_filename = "exception.json"
    mock_app_log_debug = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.GCPBatchExecutor._debug_log"
    )
    gcpbatch_executor._download_blob_to_file = AsyncMock(side_effect=Exception("error"))

    with pytest.raises(Exception):
        await gcpbatch_executor.query_task_exception(exception_filename)

    mock_app_log_debug.assert_called_once()


@pytest.mark.asyncio
async def test_query_task_exception(gcpbatch_executor, mocker):
    """Testing querying exception file from bucket"""
    exception_filename = "exception.json"
    gcpbatch_executor._download_blob_to_file = AsyncMock(return_value=exception_filename)
    mock_file_open = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.open")
    mock_json_load = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.json.load")

    res = await gcpbatch_executor.query_task_exception(exception_filename)
    gcpbatch_executor._download_blob_to_file.assert_called_once_with(
        gcpbatch_executor.bucket_name, exception_filename
    )
    mock_json_load.assert_called_once()
    mock_file_open.assert_called_once_with(exception_filename, "r")

    assert res == mock_json_load.return_value


@pytest.mark.asyncio
async def test_query_result_raises_exception(gcpbatch_executor, mocker):
    """Test exception handling when querying task result raises an exception"""
    result_filename = "result.pkl"
    gcpbatch_executor._download_blob_to_file = AsyncMock(side_effect=Exception("error"))
    with pytest.raises(Exception):
        await gcpbatch_executor.query_result(result_filename)

    gcpbatch_executor._download_blob_to_file.assert_called_once_with(
        gcpbatch_executor.bucket_name, result_filename
    )


@pytest.mark.asyncio
async def test_query_result(gcpbatch_executor, mocker):
    """Test querying result of the task"""
    result = 0
    result_filename = "result.pkl"
    gcpbatch_executor._download_blob_to_file = AsyncMock(return_value=result_filename)
    mock_file_open = mocker.patch("covalent_gcpbatch_plugin.gcpbatch.open")
    mock_pickle_load = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.pickle.load", return_value=result
    )

    res = await gcpbatch_executor.query_result(result_filename)

    gcpbatch_executor._download_blob_to_file.assert_awaited_once_with(
        gcpbatch_executor.bucket_name, result_filename
    )
    mock_file_open.assert_called_once_with(result_filename, "rb")
    mock_pickle_load.assert_called_once()
    assert res == result


@pytest.mark.asyncio
async def test_cancel(gcpbatch_executor, mocker):
    """Test task cancellation"""
    dispatch_id = "abcdef"
    node_id = 0
    job_handle = "batch_job"
    mock_get_batch_client = mocker.patch(
        "covalent_gcpbatch_plugin.gcpbatch.GCPBatchExecutor._get_batch_client",
        return_value=AsyncMock(),
    )

    await gcpbatch_executor.cancel({"dispatch_id": dispatch_id, "node_id": node_id}, job_handle)
    mock_get_batch_client.assert_called_once()
    mock_get_batch_client.return_value.delete_job.assert_awaited_once_with(
        name=f"projects/{gcpbatch_executor.project_id}/locations/{gcpbatch_executor.region}/jobs/{job_handle}"
    )
