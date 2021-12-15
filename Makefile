UNITTEST_REGISTRY_HOST=http://localhost:5000

.PHONY: test
test: setup-integration
	export UNITTEST_REGISTRY_HOST
	UNITTEST_REGISTRY_HOST=${UNITTEST_REGISTRY_HOST} pytest --cov=moby_distribution --pdb
	docker-compose -f tests/integration/docker-compose.yaml down --remove-orphans -v

.PHONY: setup-integration
setup-integration:
	docker-compose -f tests/integration/docker-compose.yaml up -d --remove-orphans --force-recreate
	docker tag registry:2.7.1 localhost:5000/registry:2.7.1
	docker push localhost:5000/registry:2.7.1
