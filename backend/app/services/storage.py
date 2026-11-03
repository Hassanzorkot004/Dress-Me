import uuid
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import get_settings


class StorageService:
    """Upload to Supabase Storage when configured, with legacy S3 and explicit
    local-disk modes retained as alternatives. Local files are served through
    StaticFiles (see app/main.py); no implicit disk fallback is used.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_configured(self) -> bool:
        supabase_key = self.settings.supabase_secret_key or self.settings.supabase_service_role_key
        return bool(
            (self.settings.supabase_url and supabase_key)
            or (self.settings.aws_access_key_id and self.settings.aws_secret_access_key)
            or self.settings.local_storage_dir
        )

    def upload_image(self, file_bytes: bytes, content_type: str) -> str:
        supabase_key = self.settings.supabase_secret_key or self.settings.supabase_service_role_key
        has_supabase_config = bool(self.settings.supabase_url or supabase_key)
        if has_supabase_config and not (self.settings.supabase_url and supabase_key):
            raise RuntimeError("Set both SUPABASE_URL and SUPABASE_SECRET_KEY (or SUPABASE_SERVICE_ROLE_KEY)")

        if self.settings.supabase_url and supabase_key:
            return self._upload_supabase(file_bytes, content_type, supabase_key)

        has_access_key = bool(self.settings.aws_access_key_id)
        has_secret_key = bool(self.settings.aws_secret_access_key)
        if has_access_key != has_secret_key:
            raise RuntimeError("Set both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY for cloud storage")

        # Prefer cloud storage when configured, including during local development.
        # This lets local and hosted backends share image URLs while preserving an
        # explicit disk-only mode when no cloud credentials are available.
        if has_access_key and has_secret_key:
            if (
                self.settings.storage_endpoint_url
                and ".storage.supabase.co" in self.settings.storage_endpoint_url
                and not self.settings.storage_public_url
            ):
                raise RuntimeError(
                    "STORAGE_PUBLIC_URL is required for Supabase Storage public buckets"
                )

            key = f"{uuid.uuid4()}"
            client = _get_s3_client()
            client.put_object(
                Bucket=self.settings.storage_bucket,
                Key=key,
                Body=file_bytes,
                ContentType=content_type,
            )
            return self._public_url(key)

        if self.settings.local_storage_dir:
            return self._upload_local(file_bytes, content_type)

        raise RuntimeError("Storage backend not configured (cloud credentials or LOCAL_STORAGE_DIR required)")

    def _upload_supabase(self, file_bytes: bytes, content_type: str, api_key: str) -> str:
        extension = "png" if content_type == "image/png" else "jpg"
        key = f"{uuid.uuid4()}.{extension}"
        base_url = self.settings.supabase_url.rstrip("/")
        bucket = quote(self.settings.storage_bucket, safe="")
        object_path = quote(key, safe="/")
        headers = {
            "apikey": api_key,
            "Content-Type": content_type,
            "x-upsert": "false",
        }
        # Legacy service_role keys are JWTs and act as the Authorization identity.
        # Current sb_secret_* keys belong in apikey only and are not JWTs.
        if not api_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {api_key}"

        response = httpx.post(
            f"{base_url}/storage/v1/object/{bucket}/{object_path}",
            headers=headers,
            content=file_bytes,
            timeout=30.0,
        )
        if not response.is_success:
            detail = response.text[:500]
            raise RuntimeError(
                f"Supabase Storage upload failed ({response.status_code}): {detail}"
            )

        return f"{base_url}/storage/v1/object/public/{bucket}/{object_path}"

    def _upload_local(self, file_bytes: bytes, content_type: str) -> str:
        extension = "png" if content_type == "image/png" else "jpg"
        key = f"{uuid.uuid4()}.{extension}"
        directory = Path(self.settings.local_storage_dir)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / key).write_bytes(file_bytes)
        return f"{self.settings.public_base_url.rstrip('/')}/media/{key}"

    def _public_url(self, key: str) -> str:
        if self.settings.storage_public_url:
            return f"{self.settings.storage_public_url.rstrip('/')}/{key}"
        if self.settings.storage_endpoint_url:
            return f"{self.settings.storage_endpoint_url.rstrip('/')}/{self.settings.storage_bucket}/{key}"
        return f"https://{self.settings.storage_bucket}.s3.{self.settings.aws_region}.amazonaws.com/{key}"


@lru_cache
def _get_s3_client():
    import boto3
    from botocore.config import Config

    settings = get_settings()
    # Non-AWS S3-compatible endpoints (MinIO, DigitalOcean Spaces, ...) generally
    # don't support virtual-hosted-style addressing (bucket.endpoint.tld) since
    # that'd need wildcard DNS for the endpoint — path-style (endpoint.tld/bucket)
    # is what actually works against them.
    client_config = Config(s3={"addressing_style": "path"}) if settings.storage_endpoint_url else None
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.storage_endpoint_url,
        config=client_config,
    )
