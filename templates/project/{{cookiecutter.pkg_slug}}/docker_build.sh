#!/usr/bin/env bash

# PROJECT_ID: Your Google Cloud Project ID.  If you don't have one, create a project through the Google Cloud Console.
# IMAGE_REPO_NAME: where the image will be stored on Cloud Container Registry
# IMAGE_TAG: an easily identifiable tag for your docker image
# IMAGE_URI: the complete URI location for Cloud Container Registry
export PROJECT_ID=my-google-cloud-project
export IMAGE_REPO_NAME={{cookiecutter.pkg_slug}}-repo
export IMAGE_TAG={{cookiecutter.pkg_slug}}-app
export IMAGE_URI=gcr.io/${PROJECT_ID}/${IMAGE_REPO_NAME}:${IMAGE_TAG}

docker build -f Dockerfile -t $IMAGE_URI .