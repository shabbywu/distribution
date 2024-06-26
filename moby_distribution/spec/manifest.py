from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator

from moby_distribution.registry.utils import validate_media_type
from moby_distribution.spec.base import Descriptor, Platform


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

    schemaVersion: int = 1
    name: str
    tag: str
    architecture: str
    fsLayers: List[FileSystemLayer]
    history: List[Schema1History]
    signatures: Optional[List[JWS]] = None

    @staticmethod
    def content_type() -> str:
        return "application/vnd.docker.distribution.manifest.v1+prettyjws"

    @validator("schemaVersion")
    def validate_schema_version(cls, v):
        if v != 1:
            raise ValueError("schema version of ManifestSchema1 MUST be 1")
        return v


class PlatformSpec(Platform):
    """
    PlatformSpec specifies a platform where a particular image manifest is applicable.
    """

    features: Optional[List[str]] = None


class DockerManifestConfigDescriptor(Descriptor):
    @staticmethod
    def content_type() -> str:
        return "application/vnd.docker.container.image.v1+json"

    mediaType: str = "application/vnd.docker.container.image.v1+json"
    _validate_media_type = validator("mediaType", allow_reuse=True)(validate_media_type)


class DockerManifestLayerDescriptor(Descriptor):
    @staticmethod
    def content_types() -> List[str]:
        return [
            "application/vnd.docker.image.rootfs.diff.tar.gzip",
            "application/vnd.docker.image.rootfs.foreign.diff.tar.gzip",
        ]

    mediaType: str = "application/vnd.docker.image.rootfs.diff.tar.gzip"
    _validate_media_type = validator("mediaType", allow_reuse=True)(validate_media_type)


class ManifestSchema2(BaseModel):
    """image manifest for the Registry, Schema2.
    spec: https://github.com/distribution/distribution/blob/main/docs/spec/manifest-v2-2.md"""

    schemaVersion: int = 2
    mediaType: str = "application/vnd.docker.distribution.manifest.v2+json"
    config: DockerManifestConfigDescriptor
    layers: List[DockerManifestLayerDescriptor]

    @staticmethod
    def content_type() -> str:
        return "application/vnd.docker.distribution.manifest.v2+json"

    @validator("schemaVersion")
    def validate_schema_version(cls, v):
        if v != 2:
            raise ValueError("schema version of ManifestSchema2 MUST be 2")
        return v

    _validate_media_type = validator("mediaType", allow_reuse=True)(validate_media_type)


class OCIManifestConfigDescriptor(Descriptor):
    @staticmethod
    def content_type() -> str:
        return "application/vnd.oci.image.config.v1+json"

    _validate_media_type = validator("mediaType", allow_reuse=True)(validate_media_type)


class OCIManifestLayerDescriptor(Descriptor):
    @staticmethod
    def content_types() -> List[str]:
        return [
            "application/vnd.oci.image.layer.v1.tar",
            "application/vnd.oci.image.layer.v1.tar+gzip",
            "application/vnd.oci.image.layer.nondistributable.v1.tar",
            "application/vnd.oci.image.layer.nondistributable.v1.tar+gzip",
        ]

    _validate_media_type = validator("mediaType", allow_reuse=True)(validate_media_type)


class OCIManifestSchema1(BaseModel):
    """image manifest for the OCI Image

    spec: https://github.com/opencontainers/image-spec/blob/main/manifest.md
    """

    schemaVersion: int
    mediaType: str = "application/vnd.oci.image.manifest.v1+json"
    config: OCIManifestConfigDescriptor
    layers: List[OCIManifestLayerDescriptor]
    annotations: Dict[str, str] = Field(default_factory=dict)

    @staticmethod
    def content_type() -> str:
        return "application/vnd.oci.image.manifest.v1+json"

    @validator("schemaVersion")
    def validate_schema_version(cls, v):
        if v != 2:
            raise ValueError("schema version of OCIManifestSchema1 MUST be 2")
        return v

    _validate_media_type = validator("mediaType", allow_reuse=True)(validate_media_type)


class ManifestDescriptor(Descriptor):
    """ManifestDescriptor references a platform-specific manifest."""

    platform: Optional[PlatformSpec] = None
