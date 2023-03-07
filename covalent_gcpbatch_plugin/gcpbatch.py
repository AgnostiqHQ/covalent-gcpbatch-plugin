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

import os
import json
import asyncio
import cloudpickle as pickle
from google.cloud import batch_v1, storage
from google.cloud.batch_v1.types import Job
from covalent._shared_files.logger import app_log
from covalent._shared_files.config import get_config
from typing import Callable, Dict, Optional, List, Any
from covalent.executor.executor_plugins.remote_executor import RemoteExecutor
from covalent._shared_files.exceptions import TaskCancelledError

EXECUTOR_PLUGIN_NAME = "GCPBatchExecutor"

_EXECUTOR_PLUGIN_DEFAULTS = {
    "bucket_name": "",
    "container_image_uri": "",
    "service_account_email": "",
    "project_id": "",
    "region": "",
    "vcpus": 2,
    "memory": 512,
    "time_limit": 300,
    "poll_freq": 5,
    "retries": 3,
}

MOUNT_PATH = "/mnt/disks/covalent"
COVALENT_TASK_FUNC_FILENAME = "func-{dispatch_id}-{node_id}.pkl"
RESULT_FILENAME = "result-{dispatch_id}-{node_id}.pkl"
EXCEPTION_FILENAME = "exception-{dispatch_id}-{node_id}.json"
BATCH_JOB_NAME = "job-{dispatch_id}-{node_id}"


class GCPBatchExecutor(RemoteExecutor):
    """
    Google Batch Executor

    Arg(s)
        bucket_name: Google storage bucket name to hold all the intermediate objects
        container_image_uri: Container image that gets executed by the job
        service_account_email: Service account email address that gets used by the job when executing
        project_id: Google project ID
        region: Google region
        vcpus: Number of virtual CPU cores needed by the job
        memory: Memory requirement for the job in (MB)a
        time_limit: Number of seconds to wait before the job is considered to have failed
        poll_freq: Frequency with which the poll the bucket and job for results
        retries: Number of times to retry if a job fails
        cache_dir: Path to a local directory where the temporary files get stored

    Return(s)
        None
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        container_image_uri: Optional[str] = None,
        service_account_email: Optional[str] = None,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        vcpus: Optional[int] = None,
        memory: Optional[int] = None,
        time_limit: Optional[int] = None,
        poll_freq: Optional[int] = None,
        retries: Optional[int] = None,
        cache_dir: Optional[str] = None,
    ):
        self.project_id = project_id or get_config("executors.gcpbatch.project_id")
        self.region = region or get_config("executors.gcpbatch.region")
        self.bucket_name = bucket_name or get_config("executors.gcpbatch.bucket_name")
        self.container_image_uri = container_image_uri or get_config(
            "executors.gcpbatch.container_image_uri"
        )
        self.service_account_email = service_account_email or get_config(
            "executors.gcpbatch.service_account_email"
        )
        self.vcpus = vcpus or int(get_config("executors.gcpbatch.vcpus"))
        self.memory = memory or int(get_config("executors.gcpbatch.memory"))
        self.time_limit = time_limit or int(get_config("executors.gcpbatch.time_limit"))
        self.poll_freq = poll_freq or int(get_config("executors.gcpbatch.poll_freq"))
        self.retries = retries or int(get_config("executors.gcpbatch.retries"))
        self.cache_dir = cache_dir

        super().__init__(
            poll_freq=self.poll_freq,
            time_limit=self.time_limit,
            retries=self.retries,
            cache_dir=self.cache_dir,
        )

    @staticmethod
    def _get_batch_client() -> batch_v1.BatchServiceAsyncClient:
    """Retrieve batch client."""
        return batch_v1.BatchServiceAsyncClient()

    @staticmethod
    def _debug_log(msg: str) -> None:
        """Write a debug log message to log file"""
        app_log.debug(f"[GCPBatchExecutor] | {msg}")

    def _pickle_func_sync(
        self, function: Callable, args: List, kwargs: List, task_metadata: Dict
    ) -> str:
        """
        Pickle the function synchronously

        Arg(s)
            function: A Python picklable callable
            args: List of function's positional arguments
            kwargs: List of function's keyword arguments

        Return(s)
            Path to pickled object file
        """
        dispatch_id = task_metadata["dispatch_id"]
        node_id = task_metadata["node_id"]
        local_func_filename = os.path.join(
            self.cache_dir,
            COVALENT_TASK_FUNC_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id),
        )
        self._debug_log(f"Pickling function, args, and kwargs to {local_func_filename}")

        with open(local_func_filename, "wb") as f:
            pickle.dump((function, args, kwargs), f)

        return local_func_filename

    async def _pickle_func(
        self, function: Callable, args: List, kwargs: Dict, task_metadata: Dict
    ) -> str:
        """
        Pickle the function asynchronously

        Arg(s)
            function: A Python picklable callable
            args: List of function's positional arguments
            kwargs: List of function's keyword arguments

        Return(s)
            Path to pickled object file
        """
        self._debug_log("Pickling function, args and kwargs ...")
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(
            None, self._pickle_func_sync, function, args, kwargs, task_metadata
        )
        return await fut

    def _validate_credentials(self) -> bool:
    """Method to validate credentials. 
    
    TODO - Add full implementation in future phase.
    """
        return True

    def _upload_task_sync(self, func_filename: str) -> None:
        """Upload task to the google storage bucket"""
        self._debug_log(f"Uploading {func_filename} to bucket {self.bucket_name}")
        storage_client = storage.Client()
        bucket = storage_client.bucket(self.bucket_name)
        blob = bucket.blob(func_filename)
        try:
            blob.upload_from_filename(func_filename, if_generation_match=0)
        except Exception:
            app_log.exception(f"Failed to upload {func_filename} to {self.bucket_name}")
            raise

    async def _upload_task(self, func_filename: str) -> None:
        """Upload task to the google storage bucket"""
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, self._upload_task_sync, func_filename)
        return await fut

    def _create_batch_job_sync(
        self, image_uri: str, task_metadata: Dict[str, str]
    ) -> batch_v1.Job:
        """
        Create a Batch job object

        Args:
            task_metadata: Dictionary containing the dispatch_id and task node_id
        """
        dispatch_id = task_metadata["dispatch_id"]
        node_id = task_metadata["node_id"]
        app_log.debug(f"Creating Google batch job object: {dispatch_id}-{node_id}")

        task_spec = batch_v1.TaskSpec()

        # Create a runnable container object
        runnable = batch_v1.Runnable()
        runnable.container = batch_v1.Runnable.Container(image_uri=image_uri)

        # Append to task spec
        task_spec.runnables.append(runnable)

        # Setup task's environment variables
        function_filename = os.path.join(
            MOUNT_PATH,
            COVALENT_TASK_FUNC_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id),
        )
        result_filename = os.path.join(
            MOUNT_PATH, RESULT_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id)
        )
        exception_filename = os.path.join(
            MOUNT_PATH,
            EXCEPTION_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id),
        )

        task_spec.environment = batch_v1.Environment(
            variables={
                "COVALENT_TASK_FUNC_FILENAME": function_filename,
                "RESULT_FILENAME": result_filename,
                "EXCEPTION_FILENAME": exception_filename,
            }
        )

        # Mount bucket
        gcs_bucket = batch_v1.GCS()
        gcs_bucket.remote_path = self.bucket_name
        gcs_volume = batch_v1.Volume()
        gcs_volume.gcs = gcs_bucket
        gcs_volume.mount_path = MOUNT_PATH
        task_spec.volumes = [gcs_volume]

        # Specify task's compute resources
        task_spec.compute_resource = batch_v1.ComputeResource(
            cpu_milli=self.vcpus * 1000, memory_mib=self.memory
        )
        task_spec.max_retry_count = self.retries
        task_spec.max_run_duration = f"{self.time_limit}s"

        # Create task group
        task_group = batch_v1.TaskGroup(task_count=1, task_spec=task_spec)

        # Set job's allocation policies
        alloc_policy = batch_v1.AllocationPolicy(
            service_account={"email": self.service_account_email}
        )

        # Set the cloud logging policy on the job
        logs_policy = batch_v1.LogsPolicy(destination="CLOUD_LOGGING")

        return batch_v1.Job(
            task_groups=[task_group],
            allocation_policy=alloc_policy,
            logs_policy=logs_policy,
        )

    async def _create_batch_job(
        self, image_uri: str, task_metadata: Dict[str, str]
    ) -> batch_v1.Job:
        """Create a batch job asynchronously"""
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, self._create_batch_job_sync, image_uri, task_metadata)
        return await fut

    async def submit_task(self, dispatch_id: str, node_id: int, batch_job: batch_v1.Job) -> Any:
        """
        Submit a batch job to Google for execution

        Arg(s)
            dispatch_id: Dispatch ID of the workflow
            node_id: ID of the node in the lattice
            batch_job: A Google batch Job object

        Return(s)
            Google Batch job create response
        """
        batch_client = self._get_batch_client()

        create_request = batch_v1.CreateJobRequest()
        create_request.job = batch_job
        create_request.job_id = BATCH_JOB_NAME.format(dispatch_id=dispatch_id, node_id=node_id)
        create_request.parent = f"projects/{self.project_id}/locations/{self.region}"

        return await batch_client.create_job(create_request)

    async def get_job_state(self, job_name: str) -> str:
        """
        Get the job's state

        Arg(s)
            job_name: Name of the batch job

        Return(s):
           job_state_name: String representing the state of the batch job
        """
        batch_client = self._get_batch_client()
        job_description = await batch_client.get_job(
            name=f"projects/{self.project_id}/locations/{self.region}/jobs/{job_name}"
        )
        return job_description.status.state.name

    async def run(self, function: Callable, args: List, kwargs: Dict, task_metadata: Dict) -> Any:
        """
        Run the task by the executor

        Arg(s)
            function: Callable that represents the electron's computation
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            task_metadata: Dictionary containing the dispatch and node id for the task

        Return(s)
            Result object
        """
        dispatch_id = task_metadata["dispatch_id"]
        node_id = task_metadata["node_id"]
        batch_job_name = BATCH_JOB_NAME.format(dispatch_id=dispatch_id, node_id=node_id)
        result_filename = RESULT_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id)
        exception_filename = EXCEPTION_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id)

        # Pickle the function, args and kwargs
        if not await self.get_cancel_requested():
            local_func_filename = await self._pickle_func(function, args, kwargs, task_metadata)
        else:
            self._debug_log(f"TASK CANCELLED")
            raise TaskCancelledError(f"Batch job {batch_job_name} requested to be cancelled")

        # Upload the pickled function, args & kwargs to storage bucket
        if not await self.get_cancel_requested():
            self._debug_log(f"Uploading {local_func_filename} to {self.bucket_name}")
            await self._upload_task(local_func_filename)
        else:
            raise TaskCancelledError(f"Batch job {batch_job_name} requested to be cancelled")

        # Create Batch job
        if not await self.get_cancel_requested():
            self._debug_log(f"Creating batch job")
            batch_job = await self._create_batch_job(
                image_uri=self.container_image_uri, task_metadata=task_metadata
            )
        else:
            raise TaskCancelledError(f"Batch job {batch_job_name} requested to be cancelled")

        # Submit Batch job
        if not await self.get_cancel_requested():
            batch_job = await self.submit_task(dispatch_id, node_id, batch_job)
            self._debug_log(f"Submitted batch job {batch_job.uid}")
        else:
            raise TaskCancelledError(f"Batch job {batch_job_name} requested to be cancelled")

        self._debug_log(f"Saving job handle {batch_job_name} to the database")
        await self.set_job_handle(handle=batch_job_name)

        # Poll task for result or exception
        self._debug_log(f"Polling task for {result_filename} or {exception_filename}")
        object_key = await self._poll_task(task_metadata, result_filename, exception_filename)

        if object_key == exception_filename:
            # Download the raised exception
            self._debug_log(
                f"Retrieving exception raised during task exceution - {dispatch_id}:{node_id}"
            )
            exception = await self.query_task_exception(exception_filename)
            raise RuntimeError(exception)

        if object_key == result_filename:
            # Download the result object
            self._debug_log(f"Retrieving result for task - {dispatch_id}:{node_id}")
            result_object = await self.query_result(result_filename)
            return result_object

    def _get_status_sync(self, object_key: str) -> bool:
        """
        Check the status of the objects in the bucket

        Arg(s)
            object_keys: Name of the objects to check for in the bucket

        Return(s)
            List of bools indicating if the exists or not
        """
        storage_client = storage.Client()
        blobs = storage_client.list_blobs(self.bucket_name)
        blob_names = [blob.name for blob in blobs]
        return True if object_key in blob_names else False

    async def get_status(self, object_key: str) -> bool:
        """
        Run get status sync asynchronously

        Arg(s)
            object_keys: Name of the objects to check for in the bucket

        Return(s)
            List of bools indicating if the exists or not
        """
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, self._get_status_sync, object_key)
        return await fut

    async def _poll_task(
        self, task_metadata: Dict, result_filename: str, exception_filename: str
    ) -> Optional[str]:
        """
        Poll task until its result is ready

        Arg(s):
            object_key: Name of the object to check if its present in the bucket

        Return(s):
            object_key
        """
        dispatch_id = task_metadata["dispatch_id"]
        node_id = task_metadata["node_id"]
        job_name = BATCH_JOB_NAME.format(dispatch_id=dispatch_id, node_id=node_id)

        time_left = self.time_limit
        while time_left > 0:
            state_name = await self.get_job_state(job_name)
            self._debug_log(f"Job {job_name} state {state_name}")
            # Check if get cancel requested is true and the job is in deletion mode
            if state_name == "DELETION_IN_PROGRESS" and await self.get_cancel_requested():
                raise TaskCancelledError(f"Batch job {job_name} cancelled")
            elif state_name == "SUCCEEDED":
                # Look for the result object
                self._debug_log(f"Polling {job_name} for {result_filename}")
                object_status = await self.get_status(result_filename)
                if object_status:
                    return result_filename
            elif state_name == "FAILED":
                # Look for the exception object
                self._debug_log(f"Polling {job_name} for {exception_filename}")
                object_status = await self.get_status(exception_filename)
                if object_status:
                    return exception_filename
            elif state_name == "STATE_UNSPECIFIED":
                raise RuntimeError(f"Job {job_name} left in an unspecified state")
            else:
                await asyncio.sleep(self.poll_freq)
                time_left -= self.poll_freq
                continue

        raise TimeoutError(f"Batch job {job_name} timed out")

    def _download_blob_to_file_sync(self, bucket_name: str, blob_name: str) -> Optional[str]:
        """
        Download a blob from the storage bucket to local filesystem in the cache directory

        Arg(s)
            bucket_name: Name of the storage bucket to download the blob from
            blob_name: Name of the blob object to download
            download_dir: Directory to download the blob to locally

        Return(s)
            None
        """
        local_blob_filename = os.path.join(self.cache_dir, blob_name)
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.download_to_filename(local_blob_filename)
            return local_blob_filename
        except Exception as ex:
            self._debug_log(str(ex))
            raise

    async def _download_blob_to_file(self, bucket_name: str, blob_name: str) -> Optional[str]:
        """
        Download a blob from the storage bucket to local filesystem in the cache directory asynchronously

        Arg(s)
            bucket_name: Name of the storage bucket to download the blob from
            blob_name: Name of the blob object to download
            download_dir: Directory to download the blob to locally

        Return(s)
            None
        """
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, self._download_blob_to_file_sync, bucket_name, blob_name)
        return await fut

    async def query_task_exception(self, exception_filename: str) -> Optional[str]:
        """
        Fetch the exception raised by the task from the storage bucket

        Arg(s)
            exception_filename: Name of the exception file to be downloaded from the storage bucket into the cache_dir

        Return(s)
            json string of the exception raised by the task
        """

        try:
            local_exception_filename = await self._download_blob_to_file(
                self.bucket_name, exception_filename
            )
            with open(local_exception_filename, "r") as f:
                task_exception = json.load(f)

            return task_exception
        except Exception as ex:
            self._debug_log(str(ex))
            raise

    async def query_result(self, result_filename: str) -> Any:
        """
        Fetch the result object from the storage bucket asynchronously

        Arg(s)
           result_filename: Name of the result filename stored in the storage bucket

        Return(s)
            Result object from the task
        """
        try:
            local_result_filename = await self._download_blob_to_file(
                self.bucket_name, result_filename
            )
            with open(local_result_filename, "rb") as f:
                result_object = pickle.load(f)
            return result_object
        except Exception as ex:
            self._debug_log(str(ex))
            raise

    async def cancel(self, task_metadata: Dict, job_handle: str) -> None:
        """
        Cancel the batch job

        Arg(s)
            task_metadata: Dictionary with the task's dispatch_id and node id
            job_handle: Unique job handle assigned to the task by Batch

        Return(s)
            None
        """
        batch_client = self._get_batch_client()
        await batch_client.delete_job(
            name=f"projects/{self.project_id}/locations/{self.region}/jobs/{job_handle}"
        )
