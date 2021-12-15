from moby_distribution.spec import manifest


def test_docker_schema1(docker_manifest_schema1_dict):
    assert manifest.ManifestSchema1(**docker_manifest_schema1_dict).dict() == docker_manifest_schema1_dict


def test_docker_schema2(docker_manifest_schema2_dict):
    assert (
        manifest.ManifestSchema2(**docker_manifest_schema2_dict).dict(exclude_unset=True)
        == docker_manifest_schema2_dict
    )


def test_oci_schema1(oci_manifest_schema1_dict):
    assert (
        manifest.OCIManifestSchema1(**oci_manifest_schema1_dict).dict(exclude_unset=True) == oci_manifest_schema1_dict
    )
