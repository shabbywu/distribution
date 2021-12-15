from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Platform(BaseModel):
    """
    Platform describes the platform which the image in the manifest runs on.
    """

    architecture: str
    os: str
    os_version: str = Field(alias="os.version")
    os_features: Optional[List[str]] = Field(alias="os.features")
    variant: str


class Descriptor(BaseModel):
    """
    Descriptor describes targeted content. Used in conjunction with a blob
    store, a descriptor can be used to fetch, store and target any kind of
    blob. The struct also describes the wire protocol format. Fields should
    only be added but never changed.

    spec: https://github.com/distribution/distribution/blob/cc4627fc6e5f20cfe8534492b44331fa16ccf872/blobs.go#L61
    see also: https://github.com/opencontainers/image-spec/blob/main/descriptor.md
    """

    mediaType: str
    size: int
    digest: str
    urls: List[str] = Field(default_factory=list)
    annotations: Dict[str, str] = Field(default_factory=dict)
    platform: Optional[Platform]
