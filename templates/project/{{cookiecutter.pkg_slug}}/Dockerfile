MAINTAINER {{cookiecutter.author_name}} "{{cookiecutter.author_email}}"

# Install the nightly version of tensorflow
FROM tensorflow/tensorflow:nightly-py3
WORKDIR /app

# Installs pandas, google-cloud-storage, and scikit-learn
# scikit-learn is used when loading the data
RUN pip install pandas scikit-learn keras google-cloud-storage cloudml-hypertune

# Install curl
RUN apt-get update; apt-get install curl -y

# Copies the code for your package to the Docker image.
COPY  . .

# Installs your package on the Docker image
RUN pip install --editable .

# This assumes you're running from package
#ENTRYPOINT ["python", "{{cookiecutter.pkg_slug}}/{{cookiecutter.docker_entrypoint_script_name}}.py"]

# This is a script which is configured by {{cookiecutter.pkg_slug}}/setup.py >> setup >> entry_points
# And placed on your path when you install your package.
ENTRYPOINT["{{cookiecutter.pkg_slug}}_docker_entry"]
