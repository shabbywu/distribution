import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FileSystemLayer(BaseModel):
    blobSum: str


class JWS(BaseModel):
    header: Dict
    protected: str
    signature: str


class Schema1History(BaseModel):
    """V1Compatibility is the raw V1 compatibility information.
    This will contain the JSON object describing the V1 of this image."""

    v1Compatibility: str


class ManifestSchema1(BaseModel):
    """image manifest for the Registry, Schema1.
    spec: https://github.com/distribution/distribution/blob/main/docs/spec/manifest-v2-1.md
    """

    schemaVersion: int
    name: str
    tag: str
    architecture: str
    fsLayers: List[FileSystemLayer]
    history: List[Schema1History]
    signatures: Optional[List[JWS]]

    @property
    def content_type(self) -> str:
        return "application/vnd.docker.distribution.manifest.v1+prettyjws"


class Platform(BaseModel):
    architecture: str
    os: str
    os_version: str = Field(alias="os.version")
    os_features: Optional[List[str]] = Field(alias="os.features")
    variant: str
    features: Optional[List[str]]


class PlatformManifest(BaseModel):
    """Image Manifest for specific platform"""

    mediaType: str
    size: int
    digest: str
    platform: Platform


class ManifestConfig(BaseModel):
    mediaType: str = "application/vnd.docker.container.image.v1+json"
    size: int
    digest: str


class ManifestLayer(BaseModel):
    mediaType: str = "application/vnd.docker.image.rootfs.diff.tar.gzip"
    size: str
    digest: str


class ManifestSchema2(BaseModel):
    """image manifest for the Registry, Schema2.
    spec: https://github.com/distribution/distribution/blob/main/docs/spec/manifest-v2-2.md"""

    schemaVersion: int
    mediaType: str = "application/vnd.docker.distribution.manifest.v2+json"
    config: ManifestConfig
    layers: List[ManifestLayer]

    @property
    def content_type(self) -> str:
        return "application/vnd.docker.distribution.manifest.v2+json"
