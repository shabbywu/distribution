from moby_distribution.registry.resources.tags import Tags


class TestTags:
    def test_list(self, repo, reference, registry_client):
        assert Tags(repo=repo, client=registry_client).list() == [reference]

    def test_get(self, repo, reference, registry_client, registry_manifest_schema2_metadata):
        assert (
            Tags(repo=repo, client=registry_client).get(reference).dict(exclude_unset=True)
            == registry_manifest_schema2_metadata
        )
