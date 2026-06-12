from __future__ import annotations

import os
import pathlib
from typing import Any


def save_to_local(file_path: str, content: bytes) -> None:
    """Save content to the local filesystem.

    If the target directory does not exist, it will be created automatically.
    """
    path = pathlib.Path(file_path)
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _import_boto3() -> Any:
    try:
        import boto3  # type: ignore[import-not-found]
        return boto3
    except ImportError as exc:
        raise RuntimeError("boto3가 필요합니다. pip install boto3를 실행하세요.") from exc


def save_to_rustfs(
    file_path: str,
    content: bytes,
    *,
    bucket: str | None = None,
    object_key: str | None = None,
    region_name: str | None = None,
    endpoint_url: str | None = None,
    access_key_id: str | None = None,
    secret_access_key: str | None = None,
) -> None:
    """Save content to both local filesystem and RustFS object storage.

    Local saving is performed first. RustFS parameters are resolved from
    explicit arguments, then DATAGOKR_RUSTFS_* and RUSTFS_* environment variables,
    falling back to standard defaults if not specified.
    """
    # 1. Save locally first
    save_to_local(file_path, content)

    # 2. Resolve RustFS S3 settings
    resolved_bucket = (
        bucket
        or os.getenv("DATAGOKR_RUSTFS_BUCKET")
        or os.getenv("RUSTFS_BUCKET")
        or "datagokr-uploads"
    )
    resolved_endpoint = (
        endpoint_url
        or os.getenv("DATAGOKR_RUSTFS_ENDPOINT_URL")
        or os.getenv("RUSTFS_ENDPOINT_URL")
    )
    resolved_access_key = (
        access_key_id
        or os.getenv("DATAGOKR_RUSTFS_ACCESS_KEY_ID")
        or os.getenv("RUSTFS_ACCESS_KEY_ID")
    )
    resolved_secret_key = (
        secret_access_key
        or os.getenv("DATAGOKR_RUSTFS_SECRET_ACCESS_KEY")
        or os.getenv("RUSTFS_SECRET_ACCESS_KEY")
    )
    resolved_region = (
        region_name
        or os.getenv("DATAGOKR_RUSTFS_REGION_NAME")
        or os.getenv("RUSTFS_REGION_NAME")
        or "us-east-1"
    )
    resolved_key = object_key or pathlib.Path(file_path).name

    # 3. Dynamic import boto3 to avoid hard dependency at import time
    boto3 = _import_boto3()

    # 4. Initialize S3 client

    kwargs: dict[str, Any] = {
        "region_name": resolved_region,
    }
    if resolved_endpoint:
        kwargs["endpoint_url"] = resolved_endpoint
    if resolved_access_key and resolved_secret_key:
        kwargs["aws_access_key_id"] = resolved_access_key
        kwargs["aws_secret_access_key"] = resolved_secret_key

    try:
        s3_client = boto3.client("s3", **kwargs)
        s3_client.put_object(
            Bucket=resolved_bucket,
            Key=resolved_key,
            Body=content,
        )
    except Exception as exc:
        raise RuntimeError(
            f"RustFS 업로드 실패 (bucket={resolved_bucket!r}, key={resolved_key!r}): {exc}"
        ) from exc
