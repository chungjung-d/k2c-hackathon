from __future__ import annotations

from io import BytesIO
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from .config import settings


def _parse_endpoint(endpoint: str) -> tuple[str, bool]:
    parsed = urlparse(endpoint)
    if parsed.scheme:
        host = parsed.netloc
        secure = parsed.scheme == "https"
    else:
        host = endpoint
        secure = False
    return host, secure


def get_client() -> Minio:
    host, secure = _parse_endpoint(settings.s3_endpoint)
    return Minio(
        host,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        secure=secure,
        region=settings.s3_region,
    )


def ensure_bucket(client: Minio | None = None) -> None:
    client = client or get_client()
    found = client.bucket_exists(settings.s3_bucket)
    if not found:
        client.make_bucket(settings.s3_bucket)


def put_bytes(object_key: str, data: bytes, content_type: str | None = None) -> None:
    client = get_client()
    ensure_bucket(client)
    client.put_object(
        settings.s3_bucket,
        object_key,
        BytesIO(data),
        length=len(data),
        content_type=content_type or "application/octet-stream",
    )


def get_bytes(object_key: str) -> bytes:
    client = get_client()
    response = client.get_object(settings.s3_bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def stat_object(object_key: str) -> dict | None:
    client = get_client()
    try:
        stat = client.stat_object(settings.s3_bucket, object_key)
    except S3Error:
        return None
    return {
        "etag": stat.etag,
        "size": stat.size,
        "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
        "content_type": stat.content_type,
    }
