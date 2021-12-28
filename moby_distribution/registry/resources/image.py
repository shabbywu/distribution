import gzip
import hashlib
import io
import json
import shutil
import tarfile
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from moby_distribution.registry.client import DockerRegistryV2Client, default_client
from moby_distribution.registry.resources import RepositoryResource
from moby_distribution.registry.resources.blobs import Blob, HashSigner
from moby_distribution.registry.resources.manifests import ManifestRef
from moby_distribution.registry.utils import generate_temp_dir
from moby_distribution.spec.image_json import ImageJSON
from moby_distribution.spec.manifest import (
    DockerManifestConfigDescriptor,
    DockerManifestLayerDescriptor,
    ManifestSchema2,
)


class ImageManifest(BaseModel):
    config: str = Field(default="", alias="Config")
    RepoTags: List[str] = Field(default_factory=list)
    Layers: List[str] = Field(default_factory=list)


class LayerRef(BaseModel):
    repo: str = ""
    digest: str = ""
    size: int = -1
    exists: bool = True
    local_path: Optional[Path]


class ImageRef(RepositoryResource):
    """ImageRef is used to Manipulate Docker images"""

    def __init__(
        self,
        repo: str,
        reference: str,
        layers: List[LayerRef],
        initial_config: str,
        client: DockerRegistryV2Client = default_client,
    ):
        super().__init__(repo, client)
        self.reference = reference
        self.layers = layers
        self._initial_config = initial_config
        self._dirty = False
        # diff id is the digest of uncompressed tarball
        self._append_diff_ids: List[str] = []

    @classmethod
    def from_image(
        cls,
        from_repo: str,
        from_reference: str,
        to_repo: Optional[str] = None,
        to_reference: Optional[str] = None,
        client: DockerRegistryV2Client = default_client,
    ):
        """Initial a `ImageRef` from `{from_repo}:{from_reference}` but will name `{to_repo, to_reference}`

        if no `to_repo` or `to_reference` given, use `from_repo` or `from_reference` as default.
        """
        if to_repo is None:
            to_repo = from_repo
        if to_reference is None:
            to_reference = from_reference
        manifest = ManifestRef(repo=from_repo, reference=from_reference, client=client).get(
            ManifestSchema2.content_type()
        )
        layers = [
            LayerRef(repo=from_repo, digest=layer.digest, size=layer.size, exists=True) for layer in manifest.layers
        ]

        fh = io.BytesIO()
        Blob(repo=from_repo, digest=manifest.config.digest, client=client, fileobj=fh).download()
        fh.seek(0)

        return cls(
            repo=to_repo, reference=to_reference, layers=layers, initial_config=fh.read().decode(), client=client
        )

    def save(self, dest: str):
        """save the image to dest, as Docker Image Specification v1.2 Format

        spec: https://github.com/moby/moby/blob/master/image/spec/v1.2.md
        """
        if self._dirty:
            raise Exception("Can't download temporary image")

        manifest = ImageManifest(RepoTags=[f"{self.repo}:{self.reference}"])
        with generate_temp_dir() as workplace:
            # Step 1. save image json
            image_json_digest = hashlib.sha256(self.image_json_str.encode()).hexdigest()

            manifest.config = f"{image_json_digest}.json"
            (workplace / manifest.config).write_text(self.image_json_str)

            # Step 2. download layers
            for layer in self.layers:
                manifest.Layers.append(self._save_layer(workplace, layer=layer))

            # Step 3. save manifest
            (workplace / "manifest.json").write_text(f"[{manifest.json(by_alias=True)}]")

            # Step 4. save as tar
            with tarfile.open(mode="w", name=dest) as tarball:
                for f in workplace.iterdir():
                    tarball.add(name=str(f.absolute()), arcname=str(f.relative_to(workplace)))
        return dest

    def push(self, media_type: str = ManifestSchema2.content_type()):
        """push the image to the registry."""
        if media_type == ManifestSchema2.content_type():
            return self.push_v2()
        raise NotImplementedError("only support push images with Manifest Schema2.")

    def push_v2(self) -> ManifestSchema2:
        """push the image to the registry, with Manifest Schema2."""
        layer_descriptors = []
        # Step 1: upload all layers
        for layer in self.layers:
            layer_descriptors.append(self._upload_layer(layer))

        # Step 2: upload the image json
        config_descriptor = self._upload_config(self.image_json_str)

        # Step 3.: upload the manifest
        manifest = ManifestSchema2(config=config_descriptor, layers=layer_descriptors)
        ManifestRef(repo=self.repo, reference=self.reference, client=self.client).put(manifest)
        return manifest

    def add_layer(self, layer: LayerRef) -> DockerManifestLayerDescriptor:
        """Add a layer to this image.

        Step:
          1. calculate the sha256 sum for the gzipped_tarball, as digest
          2. calculate the sha256 sum for the uncompressed_tarball, as diff_id
        """
        if not layer.exists and not layer.local_path:
            raise ValueError("Unknown layer")

        uncompressed_tarball_signer = HashSigner(fh=io.BytesIO())
        # Add local layer
        if layer.local_path:
            # Step 1: calculate the sha256 sum for the gzipped_tarball
            gzipped_tarball_signer = HashSigner()
            with layer.local_path.open(mode="rb") as gzipped:
                shutil.copyfileobj(gzipped, gzipped_tarball_signer)
                size = gzipped_tarball_signer.tell()

            # Step 2: calculate the sha256 sum for the uncompressed_tarball
            with gzip.open(filename=layer.local_path) as uncompressed:
                shutil.copyfileobj(uncompressed, uncompressed_tarball_signer)

            if layer.digest and layer.digest != gzipped_tarball_signer.digest():
                raise ValueError(
                    "Wrong digest, layer.digest<'%s'> != signer.digest<'%s'>",
                    layer.digest,
                    gzipped_tarball_signer.digest(),
                )

            layer.digest = gzipped_tarball_signer.digest()
            layer.repo = self.repo
            layer.size = size

        # Add remote layer if the layer is exists in registry
        else:
            with generate_temp_dir() as temp_dir:
                # Step 1: calculate the sha256 sum for the gzipped_tarball
                with (temp_dir / "blob").open(mode="wb") as fh:
                    gzipped_tarball_signer = HashSigner(fh=fh)
                    Blob(
                        repo=layer.repo, digest=layer.digest, client=self.client, fileobj=gzipped_tarball_signer
                    ).download()
                    size = gzipped_tarball_signer.tell()

                # Step 2: calculate the sha256 sum for the uncompressed_tarball
                with gzip.open(filename=(temp_dir / "blob")) as uncompressed:
                    shutil.copyfileobj(uncompressed, uncompressed_tarball_signer)
            if layer.size != size:
                raise ValueError("Wrong Size, layer.size<'%d'> != signer.size<'%d'>", layer.size, size)
            if layer.digest != gzipped_tarball_signer.digest():
                raise ValueError(
                    "Wrong digest, layer.digest<'%s'> != signer.digest<'%s'>",
                    layer.digest,
                    gzipped_tarball_signer.digest(),
                )

        self._dirty = True
        self._append_diff_ids.append(uncompressed_tarball_signer.digest())
        self.layers.append(layer)
        return DockerManifestLayerDescriptor(
            digest=gzipped_tarball_signer.digest(),
            size=size,
        )

    @property
    def image_json(self) -> ImageJSON:
        base = ImageJSON(**json.loads(self._initial_config))
        if not self._dirty:
            return base
        base.rootfs.diff_ids.extend(self._append_diff_ids)
        return base

    @property
    def image_json_str(self) -> str:
        if not self._dirty:
            return self._initial_config
        image_json = self.image_json
        return image_json.json(exclude_unset=True, exclude_defaults=True, separators=(",", ":"))

    def _save_layer(self, workplace: Path, layer: LayerRef) -> str:
        """Download the gzipped layer, and uncompress as the raw tarball.

        :raise RequestErrorWithResponse: raise if an error occur.
        """
        temp_gzip_path = workplace / "layers.tar.gz"
        temp_tarball_path = workplace / "layer.tar"
        Blob(repo=layer.repo, digest=layer.digest, local_path=temp_gzip_path, client=self.client).download()

        with gzip.open(filename=temp_gzip_path) as gzipped, temp_tarball_path.open(mode="wb") as fh:
            signer = HashSigner(fh)
            shutil.copyfileobj(gzipped, signer)

        tarball_path = f"{signer.digest()}/layer.tar"
        (workplace / tarball_path).parent.mkdir(exist_ok=True, parents=True)

        temp_gzip_path.unlink()
        shutil.move(str(temp_tarball_path.absolute()), str((workplace / tarball_path).absolute()))
        return tarball_path

    def _upload_layer(self, layer: LayerRef) -> DockerManifestLayerDescriptor:
        """Upload the layer to the registry
        this func will mount the existed layers from other repo or upload the local layers to the repo.

        :raise RequestErrorWithResponse: raise if an error occur.
        """

        if layer.exists and layer.repo != self.repo:
            descriptor = Blob(repo=self.repo, digest=layer.digest, client=self.client).mount_from(from_repo=layer.repo)
        elif not layer.exists:
            blob = Blob(repo=self.repo, local_path=layer.local_path, client=self.client)
            descriptor = blob.upload()
        else:
            descriptor = Blob(repo=self.repo, client=self.client).stat(layer.digest)
        return DockerManifestLayerDescriptor(
            size=descriptor.size,
            digest=descriptor.digest,
            urls=descriptor.urls,
        )

    def _upload_config(self, image_json_str: str) -> DockerManifestConfigDescriptor:
        """Upload the Image JSON to the registry

        :raise RequestErrorWithResponse: raise if an error occur.
        """
        descriptor = Blob(repo=self.repo, fileobj=io.BytesIO(image_json_str.encode()), client=self.client).upload()
        return DockerManifestConfigDescriptor(
            size=descriptor.size,
            digest=descriptor.digest,
            urls=descriptor.urls,
        )