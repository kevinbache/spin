FROM tensorflow/tensorflow:nightly-py3

RUN apt-get update && apt-get install -y curl vim

# TODO: change user from root

## Copy local code to the container image.
WORKDIR /app
COPY . .

############################
RUN mkdir /helpers
COPY copy_ssh_keys.py /helpers

## TODO: remove me
#RUN mkdir -p /secret/ssh
#COPY ./ssh_keys/ /secret/ssh/
##RUN ls -la /secret/ssh/
##RUN ls -la /secret/ssh/ssh_server_keys
##RUN ls -la /secret/ssh/user_keys
##RUN ls -la /secret/ssh/user_login_public_keys
############################

###### BEGIN GCLOUD ######
# ref: https://cloud.google.com/sdk/docs/quickstart-debian-ubuntu
RUN CLOUD_SDK_REPO="cloud-sdk-$(grep VERSION_CODENAME /etc/os-release | cut -d '=' -f 2)" && \
    echo "deb http://packages.cloud.google.com/apt $CLOUD_SDK_REPO main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
    apt-get update && apt-get install google-cloud-sdk -y
####### END GCLOUD #######

###### BEGIN KUBECTL ######
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl
RUN mv ./kubectl /usr/local/bin
####### END KUBECTL #######

RUN pip install pandas scikit-learn keras google-cloud-storage cloudml-hypertune
RUN pip install Flask gunicorn

#RUN useradd -ms /bin/bash serveuser
#USER serveuser

################# BEGIN SSH STUFF #################
# ref: https://leadwithoutatitle.wordpress.com/2018/03/07/how-to-create-an-ssh-enabled-docker-container-using-kubernetes/
# ref: https://docs.docker.com/engine/examples/running_ssh_service/
RUN apt-get update && apt-get install -y openssh-server
RUN mkdir /var/run/sshd
RUN echo 'root:MadeUpPassword' | chpasswd
#RUN sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config

## this assumes that we're mounting the public key file at /etc/ssh-keys/
##  kubectl create secret generic ssh-key-secret --from-file=ssh-privatekey=${HOME}/.ssh/id_rsa --from-file=ssh-publickey=${HOME}/.ssh/id_rsa.pub
#RUN sed -ie 's/^.*authorized_keys/AuthorizedKeysFile \/etc\/ssh-keys\/ssh-publickey/' /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

# ref: https://stackoverflow.com/questions/26286818/connecting-to-exposed-docker-container
RUN rm -f /etc/ssh/ssh_host_*_key*
# this script copies ssh keys which have been mounted as Kubernetes secrets into the right places within the container
RUN python /helpers/copy_ssh_keys.py \
    --ssh_server_keys_mountpoint=/secrets/ssh_server_keys \
    --user_keys_mountpoint=/secrets/user_keys \
    --user_login_public_keys_mountpoint=/secrets/user_login_public_keys

#RUN ls -la /etc/ssh

EXPOSE 22
################## END SSH STUFF ##################

## enable downloading from github
## ref: https://stackoverflow.com/questions/40469380/docker-how-to-deal-with-ssh-keys-known-hosts-and-authorized-keys
## TODO: do we need other services here?
RUN ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts
RUN ssh-keyscan -t rsa gitlab.com >> ~/.ssh/known_hosts
RUN ssh-keyscan -t rsa bitbucket.com >> ~/.ssh/known_hosts

# https://medium.com/@SaravSun/admatic-tech-blog-starting-multiple-services-inside-a-container-with-supervisord-16e3beb55916

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
# ssh ref: https://stackoverflow.com/questions/25135897/how-to-automatically-start-a-service-when-running-a-docker-container/32179054#32179054
EXPOSE 80
# TODO: container needs to run a web server which knows how to pull code from github and install python packages
# could also replace the hardcoded ssh-keyscan lines above with the ability to add them directly
CMD service ssh start && exec gunicorn --bind :80 --workers 1 --threads 2 app:app
#ENTRYPOINT service ssh start && /bin/bash
