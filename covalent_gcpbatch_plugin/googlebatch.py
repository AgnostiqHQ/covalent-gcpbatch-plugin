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

executor_plugin_name = "GCPBatchExecutor"

_EXECUTOR_PLUGIN_DEFAULTS = {
    "bucket_name": "CovalentStorageBucket",
    "container_image_uri": "",
    "service_account_email": "",
    "project_id": "",
    "region": "",
    "vcpus": 2,
    "memory": 512,
    "timeout": 300,
    "poll_freq": 5,
    "retries": 3,
}


MOUNT_PATH = "/mnt/disks/covalent"
COVALENT_TASK_FUNC_FILENAME = "func-{dispatch_id}-{node_id}.pkl"
RESULT_FILENAME = "result-{dispatch_id}-{node_id}.pkl"
EXCEPTION_FILENAME = "exception-{dispatch_id}-{node_id}.json"


class GCPBatchExecutor(RemoteExecutor):
    """Google Batch Executor"""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        container_image_uri: Optional[str] = None,
        service_account_email: Optional[str] = None,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        vcpus: Optional[int] = None,
        memory: Optional[int] = None,
        timeout: Optional[int] = 300,
        poll_freq: Optional[int] = 5,
        retries: Optional[int] = 1,
    ):
        self.project_id = project_id or get_config("executor.gcpbatch.project_id")
        self.region = region or get_config("executor.gcpbatch.region")
        self.bucket_name = bucket_name or get_config("executor.gcpbatch.bucket_name")
        self.container_image_uri = container_image_uri or get_config(
            "executor.gcpbatch.container_image_uri"
        )
        self.service_account_email = service_account_email or get_config(
            "executor.gcpbatch.service_account_email"
        )
        self.vcpus = vcpus or int(get_config("executor.gcpbatch.vcpus"))
        self.memory = memory or int(get_config("executor.gcpbatch.memory"))
        self.timeout = timeout or int(get_config("executor.gcpbatch.timeout"))
        self.poll_freq = poll_freq or int(get_config("executor.gcpbatch.poll_freq"))
        self.retries = retries or int(get_config("executor.gcpbatch.retries"))

        super().__init__(poll_freq=self.poll_freq)

    @staticmethod
    def _get_batch_client() -> batch_v1.BatchServiceAsyncClient:
        return batch_v1.BatchServiceAsyncClient()

    @staticmethod
    def _debug_log(msg: str) -> None:
        """Write a debug log message to log file"""
        app_log.debug(f"[GoogleBatchExecutor] | {msg}")

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

        # Specify task's compute resources
        task_spec.compute_resource = batch_v1.ComputeResource(
            cpu_milli=self.vcpus * 1000, memory_mib=self.memory
        )
        task_spec.max_retry_count = self.retries
        task_spec.max_run_duration = f"{self.timeout}s"

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

    async def _submit_job(self, batch_job: batch_v1.Job, task_metadata: Dict[str, str]) -> Job:
        dispatch_id = task_metadata["dispatch_id"]
        node_id = task_metadata["node_id"]
        job_name = f"job-{dispatch_id}-{node_id}"

        batch_client = self._get_batch_client()

        create_request = batch_v1.CreateJobRequest()
        create_request.job = batch_job
        create_request.job_id = job_name
        create_request.parent = f"projects/{self.project_id}/locations/{self.region}"

        return await batch_client.create_job(create_request)

    async def get_job_state(self, job_name: str) -> Any:
        """Get the job's state"""
        batch_client = self._get_batch_client()
        job_description = await batch_client.get_job(
            name=f"projects/{self.project_id}/locations/{self.region}/jobs/{job_name}"
        )
        return job_description.status.State

    async def run(self, function: Callable, args: List, kwargs: Dict, task_metadata: Dict) -> Any:
        dispatch_id = task_metadata["dispatch_id"]
        node_id = task_metadata["node_id"]
        result_filename = RESULT_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id)
        exception_filename = EXCEPTION_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id)

        # Pickle the function, args and kwargs
        local_func_filename = await self._pickle_func(function, args, kwargs, task_metadata)

        # Upload the pickled function, args & kwargs to storage bucket
        await self._upload_task(local_func_filename)

        # Create Batch job
        batch_job = await self._create_batch_job(
            image_uri=self.container_image_uri, task_metadata=task_metadata
        )

        # Submit Batch job
        batch_job = await self._submit_job(batch_job, task_metadata)

        # Poll task for result or exception
        object_key = await self._poll_task([result_filename, exception_filename])

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

    def _get_status_sync(self, object_keys: List[str]) -> List[bool]:
        """
        Check the status of the objects in the bucket

        Arg(s)
            object_keys: Name of the objects to check for in the bucket

        Return(s)
            List of bools indicating if the exists or not
        """
        storage_client = storage.Client()
        blobs = storage_client.list_blobs(self.bucket_name)
        return [True if object_key in blobs else False for object_key in object_keys]

    async def _get_status(self, object_keys: List[str]) -> Any:
        """
        Run get status sync asynchronously

        Arg(s)
            object_keys: Name of the objects to check for in the bucket

        Return(s)
            List of bools indicating if the exists or not
        """
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, self._get_status, object_keys)
        return await fut

    async def _poll_task(self, object_keys: List[str]) -> str:
        """
        Poll task until its result is ready

        Arg(s):
            object_key: Name of the object to check if its present in the bucket

        Return(s):
            object_key
        """
        time_left = self.time_limit
        while time_left > 0:
            for object_key in object_keys:
                self._debug_log(f"Polling object: {object_key}")
                object_status = await self._get_status(object_keys)
                if object_status:
                    return object_key
                await asyncio.sleep(self.poll_freq)
            time_left -= self.poll_freq

        raise TimeoutError(f"{object_keys} not found in {self.bucket_name}")

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
