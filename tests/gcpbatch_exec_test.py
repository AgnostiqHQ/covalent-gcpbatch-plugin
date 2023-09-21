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

from unittest.mock import MagicMock

import pytest

from covalent_gcpbatch_plugin.exec import main


def test_exec_main(mocker):
    """Test exec main that executes the pickled function with its args and kwargs"""
    mock_dict = {
        "COVALENT_TASK_FUNC_FILENAME": "func.pkl",
        "RESULT_FILENAME": "result.pkl",
        "COVALENT_BUCKET_NAME": "test_bucket",
    }
    mocker.patch.dict("covalent_gcpbatch_plugin.exec.os.environ", mock_dict)
    mock_os_path_join = mocker.patch("covalent_gcpbatch_plugin.exec.os.path.join")
    mocker.patch("covalent_gcpbatch_plugin.exec.storage.Client", return_value=MagicMock())
    mock_file_open = mocker.patch("covalent_gcpbatch_plugin.exec.open")
    mock_pickle_load = mocker.patch(
        "covalent_gcpbatch_plugin.exec.pickle.load",
        return_value=(
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ),
    )
    mock_pickle_dump = mocker.patch("covalent_gcpbatch_plugin.exec.pickle.dump")

    main()

    mock_args = mock_pickle_load.return_value[1]
    mock_kwargs = mock_pickle_load.return_value[2]

    mock_pickle_load.return_value[0].assert_called_once_with(*mock_args, **mock_kwargs)

    assert mock_os_path_join.call_count == 2
    assert mock_file_open.call_count == 2
    mock_pickle_load.assert_called_once()
    mock_pickle_dump.assert_called_once()


def test_exec_main_raises_exception(mocker):
    """Test main raising execption while executing task"""
    mock_json_dump = mocker.patch("covalent_gcpbatch_plugin.exec.json.dump")
    mock_dict = {"EXCEPTION_FILENAME": "exception.json", "COVALENT_BUCKET_NAME": "test_bucket"}
    mocker.patch.dict("covalent_gcpbatch_plugin.exec.os.environ", mock_dict)
    mocker.patch("covalent_gcpbatch_plugin.exec.storage.Client", return_value=MagicMock())
    mock_os_path_join = mocker.patch("covalent_gcpbatch_plugin.exec.os.path.join")
    mock_file_open = mocker.patch("covalent_gcpbatch_plugin.exec.open")
    mock_pickle_load = mocker.patch(
        "covalent_gcpbatch_plugin.exec.pickle.load",
        return_value=(
            MagicMock(side_effect=Exception("error")),  # function
            MagicMock(),  # args
            MagicMock(),  # kwargs
        ),
    )

    with pytest.raises(Exception):
        main()

    mock_os_path_join.assert_called()
    assert len(mock_file_open.mock_calls) == 6
    mock_json_dump.assert_called_once()
