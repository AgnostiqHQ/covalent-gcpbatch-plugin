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
import cloudpickle as pickle


def main() -> None:
    """
    Execute the pickled function generated by Covalent for the electron and upload the result object or the generated exception to the storage bucket

    Arg(s)
        None

    Return(s)
        None
    """
    try:
        func_filename = os.environ["COVALENT_TASK_FUNC_FILENAME"]
        result_filename = os.environ["RESULT_FILENAME"]
        task_mountpoint = os.environ["GCPBATCH_TASK_MOUNTPOINT"]

        local_func_filename = os.path.join(task_mountpoint, func_filename)
        local_result_filename = os.path.join(task_mountpoint, result_filename)

        # Read the function, args and kwargs from the mount path
        with open(local_func_filename, "rb") as f:
            function, args, kwargs = pickle.load(f)

        result = function(*args, *kwargs)

        # Write the result to the mount path
        with open(local_result_filename, "wb") as f:
            pickle.dump(result, f)

    except Exception as ex:
        task_mountpoint = os.environ["GCPBATCH_TASK_MOUNTPOINT"]
        exception_filename = os.environ["EXCEPTION_FILENAME"]
        local_exception_filename = os.path.join(task_mountpoint, exception_filename)
        # Write the exception to the mount path
        with open(local_exception_filename, "w") as f:
            json.dump(str(ex), f)
        raise


if __name__ == "__main__":
    main()