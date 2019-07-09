FROM tensorflow/tensorflow:1.14.0-py3

RUN apt-get update && apt-get install -y curl vim

## Copy local code to the container image.
WORKDIR /app
COPY . .

###### BEGIN GCLOUD ######
# ref: https://cloud.google.com/sdk/docs/quickstart-debian-ubuntu
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && \
    apt-get update -y && apt-get install google-cloud-sdk -y
####### END GCLOUD #######

###### BEGIN KUBECTL ######
##RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
##RUN chmod +x ./kubectl
##RUN mv ./kubectl /usr/local/bin
#RUN gcloud components install kubectl
RUN apt-get install -y kubectl
####### END KUBECTL #######

RUN pip install pandas scikit-learn keras google-cloud-storage cloudml-hypertune
RUN pip install Flask gunicorn

#RUN useradd -ms /bin/bash serveuser
#USER serveuser

################# BEGIN SSH STUFF #################
# install and start an ssh server

# ref: https://leadwithoutatitle.wordpress.com/2018/03/07/how-to-create-an-ssh-enabled-docker-container-using-kubernetes/
# ref: https://docs.docker.com/engine/examples/running_ssh_service/
RUN apt-get update && apt-get install -y openssh-server
RUN mkdir /var/run/sshd
RUN echo 'root:MadeUpPassword' | chpasswd
RUN sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

## this assumes that we're mounting the public key file at /etc/ssh-keys/
##  kubectl create secret generic ssh-key-secret --from-file=ssh-privatekey=${HOME}/.ssh/id_rsa --from-file=ssh-publickey=${HOME}/.ssh/id_rsa.pub
#RUN sed -ie 's/^.*authorized_keys/AuthorizedKeysFile \/etc\/ssh-keys\/ssh-publickey/' /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

# ref: https://stackoverflow.com/questions/26286818/connecting-to-exposed-docker-container
RUN rm -f /etc/ssh/ssh_host_*_key*
RUN ssh-keygen -t dsa -N "" -f /etc/ssh/ssh_host_dsa_key
RUN ssh-keygen -t rsa -N "" -f /etc/ssh/ssh_host_rsa_key
RUN ssh-keygen -t ecdsa -N "" -f /etc/ssh/ssh_host_ecdsa_key
RUN ssh-keygen -t ed25519 -N "" -f /etc/ssh/ssh_host_ed25519_key

RUN mkdir ~/.ssh/

EXPOSE 22
################## END SSH STUFF ##################

# https://stackoverflow.com/questions/40469380/docker-how-to-deal-with-ssh-keys-known-hosts-and-authorized-keys
# RUN ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 4 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
# ssh ref: https://stackoverflow.com/questions/25135897/how-to-automatically-start-a-service-when-running-a-docker-container/32179054#32179054
EXPOSE 80
CMD service ssh start && exec gunicorn --bind :80 --workers 1 --threads 4 spin.actions:app
