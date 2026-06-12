from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, patch

import pytest

from datagokr.client import DataGoKrClient
from datagokr.config import DataGoKrConfig
from datagokr.storage import save_to_local, save_to_rustfs


def test_save_to_local_creates_directory_and_writes_file(tmp_path: pathlib.Path) -> None:
    file_path = tmp_path / "subdir" / "test.txt"
    content = b"hello world"

    save_to_local(str(file_path), content)

    assert file_path.exists()
    assert file_path.read_bytes() == content


@patch("datagokr.storage._import_boto3")
def test_save_to_rustfs_uploads_via_mocked_boto3(
    mock_import: MagicMock,
    tmp_path: pathlib.Path,
) -> None:
    # Arrange
    mock_boto3 = MagicMock()
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    mock_import.return_value = mock_boto3

    file_path = tmp_path / "test.bin"
    content = b"data"

    # Act
    save_to_rustfs(
        str(file_path),
        content,
        bucket="my-bucket",
        object_key="my-key",
        region_name="ap-northeast-2",
        endpoint_url="http://localhost:9000",
        access_key_id="key",
        secret_access_key="secret",
    )

    # Assert local save
    assert file_path.exists()
    assert file_path.read_bytes() == content

    # Assert S3 upload
    mock_import.assert_called_once()
    mock_boto3.client.assert_called_with(
        "s3",
        region_name="ap-northeast-2",
        endpoint_url="http://localhost:9000",
        aws_access_key_id="key",
        aws_secret_access_key="secret",
    )
    mock_s3_client.put_object.assert_called_with(
        Bucket="my-bucket",
        Key="my-key",
        Body=content,
    )


@patch("datagokr.storage._import_boto3")
def test_save_to_rustfs_uses_fallback_config_and_env(
    mock_import: MagicMock,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    mock_boto3 = MagicMock()
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    mock_import.return_value = mock_boto3

    monkeypatch.setenv("DATAGOKR_RUSTFS_BUCKET", "env-bucket")
    monkeypatch.setenv("RUSTFS_ENDPOINT_URL", "http://env-endpoint")
    monkeypatch.setenv("DATAGOKR_RUSTFS_ACCESS_KEY_ID", "env-key")
    monkeypatch.setenv("RUSTFS_SECRET_ACCESS_KEY", "env-secret")
    monkeypatch.setenv("RUSTFS_REGION_NAME", "us-west-2")

    file_path = tmp_path / "test.bin"
    content = b"data"

    # Act
    save_to_rustfs(str(file_path), content)

    # Assert S3 upload fallback
    mock_boto3.client.assert_called_with(
        "s3",
        region_name="us-west-2",
        endpoint_url="http://env-endpoint",
        aws_access_key_id="env-key",
        aws_secret_access_key="env-secret",
    )
    mock_s3_client.put_object.assert_called_with(
        Bucket="env-bucket",
        Key="test.bin",
        Body=content,
    )


@patch("datagokr.storage._import_boto3")
def test_client_save_to_rustfs_delegates_with_config(
    mock_import: MagicMock,
    tmp_path: pathlib.Path,
) -> None:
    # Arrange
    mock_boto3 = MagicMock()
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    mock_import.return_value = mock_boto3

    file_path = tmp_path / "client-test.bin"
    content = b"client-data"

    config = DataGoKrConfig(
        api_key="key",
        rustfs_bucket="config-bucket",
        rustfs_region_name="ap-northeast-1",
        rustfs_endpoint_url="http://config-endpoint",
        rustfs_access_key_id="config-key",
        rustfs_secret_access_key="config-secret",
    )

    with DataGoKrClient(api_key="key") as client:
        # Override config manually for testing
        object.__setattr__(client, "config", config)

        assert client.file_data.datasets()
        assert client.special_street.endpoint == "tn_pubr_public_area_spcliz_stret_api"

        client.save_to_local(str(file_path), content)
        assert file_path.exists()
        assert file_path.read_bytes() == content

        client.save_to_rustfs(str(file_path), content, object_key="custom-key")

    mock_boto3.client.assert_called_with(
        "s3",
        region_name="ap-northeast-1",
        endpoint_url="http://config-endpoint",
        aws_access_key_id="config-key",
        aws_secret_access_key="config-secret",
    )
    mock_s3_client.put_object.assert_called_with(
        Bucket="config-bucket",
        Key="custom-key",
        Body=content,
    )


@patch("datagokr.storage._import_boto3")
def test_save_to_rustfs_raises_runtime_error_if_boto3_missing(
    mock_import: MagicMock,
    tmp_path: pathlib.Path,
) -> None:
    # Arrange
    mock_import.side_effect = RuntimeError("boto3가 필요합니다")
    file_path = tmp_path / "test.bin"

    # Act & Assert
    with pytest.raises(RuntimeError, match="boto3가 필요합니다"):
        save_to_rustfs(str(file_path), b"data")
