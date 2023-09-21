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


import json
import os

import cloudpickle as pickle
from google.cloud import storage

CACHE_DIR = "/tmp"


def main() -> None:
    """
    Execute the pickled function generated by Covalent for the electron and upload the result object or the generated exception to the storage bucket

    Arg(s)
        None

    Return(s)
        None

    """
    try:

        func_filename = os.getenv("COVALENT_TASK_FUNC_FILENAME")
        result_filename = os.getenv("RESULT_FILENAME")
        bucket_name = os.getenv("COVALENT_BUCKET_NAME")

        local_func_filename = os.path.join(CACHE_DIR, func_filename)
        local_result_filename = os.path.join(CACHE_DIR, result_filename)

        # Download function pickle object
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        # Create blobs
        func_blob = bucket.blob(func_filename)
        result_blob = bucket.blob(result_filename)

        # download function blob
        func_blob.download_to_filename(local_func_filename)

        # Read the function, args and kwargs from the mount path
        with open(local_func_filename, "rb") as f:
            function, args, kwargs = pickle.load(f)

        result = function(*args, **kwargs)

        # Write the result to the mount path
        with open(local_result_filename, "wb") as f:
            pickle.dump(result, f)

        # upload result blob
        result_blob = bucket.blob(result_filename)
        result_blob.upload_from_filename(local_result_filename, if_generation_match=0)

    except Exception as ex:
        exception_filename = os.getenv("EXCEPTION_FILENAME")
        bucket_name = os.getenv("COVALENT_BUCKET_NAME")

        # upload exception
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        exception_blob = bucket.blob(exception_filename)
        local_exception_filename = os.path.join(CACHE_DIR, exception_filename)

        # Write the exception to the mount path
        with open(local_exception_filename, "w") as f:
            json.dump(str(ex), f)
        exception_blob.upload_from_filename(local_exception_filename, if_generation_match=0)
        raise


if __name__ == "__main__":
    main()
