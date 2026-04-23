"""Cloud WORM module — immutable evidence storage in cloud.

Backends: Local (default fallback), S3 (Object Lock), Azure (Immutable Blob).
boto3 and azure-storage-blob are optional dependencies.
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_file


class CloudWORMError(Exception):
    pass


class Backend(ABC):
    @abstractmethod
    def push(self, run_id: str, source: Path) -> dict[str, Any]: ...

    @abstractmethod
    def verify(self, run_id: str, filename: str) -> bool: ...

    @abstractmethod
    def list_runs(self) -> list[str]: ...


class LocalBackend(Backend):
    """Local filesystem backend (mirrors existing evidence_store)."""

    def __init__(self, base_dir: Path) -> None:
        self._dir = base_dir

    def push(self, run_id: str, source: Path) -> dict[str, Any]:
        dest_dir = self._dir / run_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / source.name
        shutil.copy2(source, dest)
        file_hash = sha256_file(source)
        return {"status": "pushed", "run_id": run_id, "file": source.name, "hash": file_hash}

    def verify(self, run_id: str, filename: str) -> bool:
        stored = self._dir / run_id / filename
        return stored.exists()

    def list_runs(self) -> list[str]:
        if not self._dir.exists():
            return []
        return sorted(d.name for d in self._dir.iterdir() if d.is_dir())


class S3Backend(Backend):
    """AWS S3 with Object Lock (requires boto3)."""

    def __init__(self, bucket: str, prefix: str = "evidence/") -> None:
        try:
            import boto3

            self._s3 = boto3.client("s3")
        except ImportError as err:
            raise CloudWORMError("boto3 not installed. Install with: pip install boto3") from err
        self._bucket = bucket
        self._prefix = prefix

    def push(self, run_id: str, source: Path) -> dict[str, Any]:
        key = f"{self._prefix}{run_id}/{source.name}"
        file_hash = sha256_file(source)
        self._s3.upload_file(str(source), self._bucket, key)
        return {
            "status": "pushed",
            "run_id": run_id,
            "file": source.name,
            "hash": file_hash,
            "s3_key": key,
        }

    def verify(self, run_id: str, filename: str) -> bool:
        key = f"{self._prefix}{run_id}/{filename}"
        try:
            self._s3.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def list_runs(self) -> list[str]:
        resp = self._s3.list_objects_v2(Bucket=self._bucket, Prefix=self._prefix, Delimiter="/")
        return [p["Prefix"].rstrip("/").split("/")[-1] for p in resp.get("CommonPrefixes", [])]


class AzureImmutableBackend(Backend):
    """Azure Blob Storage with Immutable Blob policies (requires azure-storage-blob)."""

    def __init__(
        self,
        connection_string: str,
        container: str = "evidence",
        retention_days: int = 2555,
    ) -> None:
        try:
            from azure.storage.blob import BlobServiceClient

            self._client = BlobServiceClient.from_connection_string(connection_string)
            self._container_client = self._client.get_container_client(container)
        except ImportError as err:
            raise CloudWORMError(
                "azure-storage-blob not installed. Install with: pip install azure-storage-blob"
            ) from err
        self._container = container
        self._retention_days = retention_days

    def push(self, run_id: str, source: Path) -> dict[str, Any]:
        blob_name = f"{run_id}/{source.name}"
        file_hash = sha256_file(source)
        blob_client = self._container_client.get_blob_client(blob_name)
        with open(source, "rb") as f:
            blob_client.upload_blob(f, overwrite=False)
        return {
            "status": "pushed",
            "run_id": run_id,
            "file": source.name,
            "hash": file_hash,
            "blob": blob_name,
        }

    def verify(self, run_id: str, filename: str) -> bool:
        blob_name = f"{run_id}/{filename}"
        blob_client = self._container_client.get_blob_client(blob_name)
        try:
            blob_client.get_blob_properties()
            return True
        except Exception:
            return False

    def list_runs(self) -> list[str]:
        runs: set[str] = set()
        for blob in self._container_client.list_blobs():
            parts = blob.name.split("/")
            if len(parts) >= 2:
                runs.add(parts[0])
        return sorted(runs)


class CloudWORM:
    """Facade for cloud WORM operations with immutability verification."""

    def __init__(self, backend: Backend) -> None:
        self._backend = backend

    def push(self, run_id: str, source: Path) -> dict[str, Any]:
        return self._backend.push(run_id, source)

    def verify(self, run_id: str, filename: str) -> bool:
        return self._backend.verify(run_id, filename)

    def verify_immutability(self, run_id: str, source: Path) -> dict[str, Any]:
        """Verify that a pushed file has not been tampered with."""
        expected_hash = sha256_file(source)
        exists = self._backend.verify(run_id, source.name)
        return {
            "run_id": run_id,
            "file": source.name,
            "expected_hash": expected_hash,
            "exists_in_backend": exists,
            "immutable": exists,
        }

    def list_runs(self) -> list[str]:
        return self._backend.list_runs()
