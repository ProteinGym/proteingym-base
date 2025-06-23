from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError
from dvc.exceptions import DvcException

from pg2_dataset.io import exists


class TestExists:
    @patch("pg2_dataset.io.bytes.dvc.api.DVCFileSystem")
    def test_dvc_file_exists_false(self, mock_dvc_filesystem):
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_dvc_filesystem.return_value = mock_path_instance

        file_path = "/path/to/dataset/nonexistent.txt"

        result = exists(Path(file_path))

        assert result is False

    @patch("pg2_dataset.io.bytes.dvc.api.DVCFileSystem")
    def test_dvc_file_dvc_exception(self, mock_dvc_filesystem):
        mock_path_instance = Mock()
        mock_path_instance.exists.side_effect = DvcException("DVC error")
        mock_dvc_filesystem.return_value = mock_path_instance

        file_path = "dvc_pg2/file.txt"

        with pytest.raises(DvcException, match="^DVC error$"):
            exists(Path(file_path))

    @patch("pg2_dataset.io.bytes.CloudPath")
    def test_s3_file_exists_true(self, mock_cloudpath):
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_cloudpath.return_value = mock_path_instance

        file_path = "s3://bucket/file.txt"

        result = exists(file_path)

        assert result is True

    @patch("pg2_dataset.io.bytes.CloudPath")
    def test_s3_file_client_error(self, mock_cloudpath):
        mock_path_instance = Mock()
        mock_path_instance.exists.side_effect = ClientError(
            error_response={"Error": {"Code": "NoSuchBucket"}},
            operation_name="HeadObject",
        )
        mock_cloudpath.return_value = mock_path_instance

        file_path = "s3://bucket/file.txt"

        with pytest.raises(ClientError):
            exists(file_path)

    @patch("pg2_dataset.io.bytes.Path")
    def test_local_file_exists_true(self, mock_path):
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        file_path = "/local/path/file.txt"

        result = exists(Path(file_path))

        assert result is True

    @patch("pg2_dataset.io.bytes.Path")
    def test_local_file_os_error(self, mock_path):
        mock_path_instance = Mock()
        mock_path_instance.exists.side_effect = OSError("OS error")
        mock_path.return_value = mock_path_instance

        file_path = "/local/path/file.txt"

        with pytest.raises(OSError):
            exists(Path(file_path))
