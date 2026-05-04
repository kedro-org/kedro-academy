# Docker registry configuration
REGISTRY ?= $(shell echo $$DOCKER_REGISTRY)
IMAGE_NAME := mlrun-kedro
TAG ?= latest
FULL_IMAGE_NAME := $(REGISTRY)/$(IMAGE_NAME):$(TAG)

# Experimental kedro-datasets with MLRun support
KEDRO_MLRUN_REPO := git+https://github.com/rokatyy/kedro-plugins.git@add-mlrun-dataset


# Install kedro requirements
.PHONY: install-requirements
install-requirements:
	uv pip install -r requirements-dev.txt


# Install kedro requirements
.PHONY: install-kedro
install-kedro:
	@echo "Installing kedro requirements..."
	uv pip install -r kedro/requirements.txt


# Install experimental kedro-datasets with MLRun Dataset support
# From: https://github.com/rokatyy/kedro-plugins/tree/add-mlrun-dataset
.PHONY: install-kedro-mlrun-dataset
install-kedro-mlrun-dataset:
	@echo "Installing experimental kedro-datasets with MLRun support..."
	@echo "Source: https://github.com/rokatyy/kedro-plugins (branch: add-mlrun-dataset)"
	@echo "This may take a few minutes (cloning and building from git)..."
	pip install "git+https://github.com/rokatyy/kedro-plugins.git@add-mlrun-dataset#subdirectory=kedro-datasets"

# Build the mlrun-kedro Docker image
.PHONY: build-kedro
build-kedro:
	@echo "Building $(IMAGE_NAME) image..."
	docker build -t $(IMAGE_NAME):$(TAG) -f kedro/Dockerfile kedro/
	@if [ -n "$(REGISTRY)" ]; then \
		docker tag $(IMAGE_NAME):$(TAG) $(FULL_IMAGE_NAME); \
		echo "Tagged image as $(FULL_IMAGE_NAME)"; \
	fi

# Push the mlrun-kedro image to registry
.PHONY: push-kedro
push-kedro:
	@if [ -z "$(REGISTRY)" ]; then \
		echo "Error: DOCKER_REGISTRY environment variable is not set"; \
		exit 1; \
	fi
	@echo "Pushing $(FULL_IMAGE_NAME) to registry..."
	docker push $(FULL_IMAGE_NAME)

# Build and push in one command
.PHONY: deploy-kedro
deploy-kedro: build-kedro push-kedro
	@echo "Successfully deployed $(FULL_IMAGE_NAME)"

