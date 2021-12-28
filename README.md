# moby-distribution - Yet another moby(docker) distribution implement by python.

moby-distribution is a library for operating Docker Image Manifest and Blobs (Layers, Config, etc.).

Works for Python 3.6+.

## Usage

### Install
You can install from PyPi.

```bash
❯ pip install moby-distribution
```

Or install from GitHub for latest version.

```bash
❯ pip install https://github.com/shabbywu/distribution/archive/main.zip
```

### Introduction
The API provides several classes: `ManifestRef`, `Blob`, `Tags`, `DockerRegistryV2Client`, `APIEndpoint`, `ImageRef`

`ManifestRef` has the following methods:
- `get(media_type)` retrieve image manifest as the provided media_type
- `get_metadata(media_type)` retrieve the manifest descriptor if the manifest exists.
- `delete(raise_not_found)` Removes the manifest specified by the provided reference.
- `put(manifest)` creates or updates the given manifest.

`Blob` has the following methods:
- `download(digest)` download the blob from registry to `local_path` or `fileobj`
- `upload()` upload the blob from `local_path` or `fileobj` to the registry by streaming
- `upload_at_one_time()` upload the monolithic blob from `local_path` or `fileobj` to the registry at one time.
- `mount_from(from_repo)` mount the blob from the given repo, if the client has read access to.
- `delete(digest)` delete the blob at the registry.

`Tags` has the following methods:
- `list()` return the list of tags in the repo
- `get(tag)` retrieve the manifest descriptor identified by the tag.
- `untag(tag)` work like `ManifestRef.delete()`

`ImageRef` has the following methods:
- `from_image(from_repo, from_reference, to_repo, to_reference)` init a `ImageRef` from `{from_repo}:{from_reference}` but will name `{to_repo, to_reference}`.
- `save(dest)` save the image to dest, as Docker Image Specification v1.2 Format.
- `push(media_type="application/vnd.docker.distribution.manifest.v2+json")` push the image to the registry.
- `push_v2()` push the image to the registry, with Manifest Schema2.
- `add_layer(layer_ref)` add a layer to this image, this is a way to build a new Image.

`DockerRegistryV2Client` has the following methods:
- `from_api_endpoint(api_endpoint, username, password)` initial a client to the `api_endpoint` with `username` and `password`

`APIEndpoint` is a dataclass, you can define APIEndpoint in the following ways:
```python
from moby_distribution import APIEndpoint
# 1. Provide scheme
APIEndpoint(url="https://registry.hub.docker.com")

# 2. No scheme provided
APIEndpoint(url="registry.hub.docker.com")
```

if the scheme is missing, we will detect whether the server provides ssl and verify the certificate.

If no ssl: use http(80).
If have ssl, but certificate is invalid:
  - try to ping the registry with https(443), if success, use it
  - otherwise, downgrade to http(80)
If have ssl and valid certificate: use https(443)

We provide an anonymous client connected to Docker Official Registry as default, you can find it at `moby_distribution.default_client`,
and you can override the default client by `set_default_client(client)`.

### Example
#### 1. List Tags for the Docker Official Image `library/python`
```python
from moby_distribution import Tags

Tags(repo="library/python").list()
# ['2', '2-alpine', '2-alpine3.10', '2-alpine3.11', '2-alpine3.4', '2-alpine3.6', ...]
```

#### 2. Get Manifest for the Docker Official Image `library/python:latest`
```python
from moby_distribution import ManifestRef, ManifestSchema1, ManifestSchema2

# Get Docker Image Manifest Version 2, Schema 1
# see alse: https://github.com/distribution/distribution/blob/main/docs/spec/manifest-v2-1.md
ManifestRef(repo="library/python", reference="latest").get(ManifestSchema1.content_type())

# Get Docker Image Manifest Version 2, Schema 2
# see alse: https://github.com/distribution/distribution/blob/main/docs/spec/manifest-v2-2.md
ManifestRef(repo="library/python", reference="latest").get(ManifestSchema2.content_type())
```

#### 3. Get the Config(aka Image JSON) for the Docker Official Image `library/python:latest`
```python
from io import BytesIO
from moby_distribution import ManifestRef, Blob

# Get Docker Image Manifest Version 2, Schema 2
manifest = ManifestRef(repo="library/python", reference="latest").get()

fh = BytesIO()
Blob(fileobj=fh, repo="library/python", digest=manifest.config.digest).download()

fh.seek(0)
config = fh.read()
```

> Using the `local_path` parameter, you can download to the file system instead of memory.

### 4. Push Blobs (Layers, Config, etc.) to Docker Registry

```python
from io import BytesIO
from moby_distribution import Blob, DockerRegistryV2Client, OFFICIAL_ENDPOINT

# To upload files to Docker Registry, you must login to your account
client = DockerRegistryV2Client.from_api_endpoint(OFFICIAL_ENDPOINT, username="your-username", password="your-password")

fh = BytesIO("just a demo")

assert Blob(repo="your-username/demo", fileobj=fh).upload()
```

> Using the `local_path` parameter, you can upload blobs from the file system instead of memory.

### 5. Push Image Manifest to Docker Registry

```python
from moby_distribution import ManifestSchema2, DockerRegistryV2Client, OFFICIAL_ENDPOINT, ManifestRef

# To upload files to Docker Registry, you must login to your account
client = DockerRegistryV2Client.from_api_endpoint(OFFICIAL_ENDPOINT, username="your-username", password="your-password")

# Build the ManifestSchema2 you need to upload
manifest = ManifestSchema2(
    schemaVersion=2,
    mediaType="application/vnd.docker.distribution.manifest.v2+json",
    config={
        ...
    },
    layers=[
        ...
    ]
)

ManifestRef(repo="your-username/demo", reference="latest").put(manifest)
```

### 6. Upload the complete image to Docker Registry, Do it Yourself!
Read the process description of [the official document](https://github.com/distribution/distribution/blob/main/docs/spec/api.md#pushing-an-image)
1. Pushing the Layers as Example 4 do
2. Pushing the Config as Example 4 do
3. Pushing the Image Manifest as Example 5 do

Done, Congratulations!

**Here is another way, use the newly implemented ImageRef!**
```python
from moby_distribution import ImageRef, DockerRegistryV2Client, OFFICIAL_ENDPOINT

# To upload files to Docker Registry, you must login to your account
client = DockerRegistryV2Client.from_api_endpoint(OFFICIAL_ENDPOINT, username="your-username", password="your-password")

image_ref = ImageRef.from_image(from_repo="your-repo", from_reference="your-reference", to_reference="the-new-reference")
image_ref.push()
```
The above statement achieves the equivalent function of `docker tag {your-repo}:{your-reference} {your-repo}:{the-new-reference} && docker push {your-repo}:{the-new-reference}`

### RoadMap
- [x] implement the Distribution Client API for moby(docker)
- [x] implement the Docker Image Operator(Operator that implement Example 6)
- [ ] Command line tool for operating Image
- [ ] implement the Distribution Client API for OCI
