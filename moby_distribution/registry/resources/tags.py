from typing import List, Optional

from moby_distribution.registry.client import URLBuilder
from moby_distribution.registry.resources import RepositoryResource
from moby_distribution.registry.resources.manifests import ManifestRef
from moby_distribution.spec.manifest import ManifestDescriptor


class Tags(RepositoryResource):
    def get(self, tag: str) -> Optional[ManifestDescriptor]:
        """retrieve the ManifestDescriptor identified by the tag."""
        return ManifestRef(self.repo, reference=tag, client=self.client, timeout=self.timeout).get_metadata()

    def untag(self, tag: str) -> bool:
        """Untag removes the provided tag association"""
        return ManifestRef(self.repo, reference=tag, client=self.client, timeout=self.timeout).delete()

    def list(self) -> List[str]:
        """return the list of tags in the repo"""
        url = URLBuilder.build_tags_url(self.client.api_base_url, self.repo)
        data = self.client.get(url=url, timeout=self.timeout).json()
        return data["tags"] or []
