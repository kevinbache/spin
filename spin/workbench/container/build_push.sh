#!/usr/bin/env bash

# TODO: we need a public project to push this to
export PROJECT_ID=kb-experiment
export IMAGE_REPO_NAME=workbench
export IMAGE_TAG=latest
export IMAGE_URI="gcr.io/${PROJECT_ID}/${IMAGE_REPO_NAME}:${IMAGE_TAG}"
docker build -f Dockerfile -t ${IMAGE_URI} .
docker push ${IMAGE_URI}
#docker build -f Dockerfile -t workbench .
