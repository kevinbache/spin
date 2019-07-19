FROM tensorflow/tensorflow:nightly-py3

###### BEGIN BASICS ######
RUN apt-get update && apt-get install -y curl vim git
####### END BASICS #######

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

################# BEGIN SSH STUFF #################
# ref: https://leadwithoutatitle.wordpress.com/2018/03/07/how-to-create-an-ssh-enabled-docker-container-using-kubernetes/
# ref: https://docs.docker.com/engine/examples/running_ssh_service/
RUN apt-get update && apt-get install -y openssh-server
RUN mkdir /var/run/sshd
RUN echo 'root:MadeUpPassword' | chpasswd
RUN sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

# ref: https://stackoverflow.com/questions/26286818/connecting-to-exposed-docker-container
RUN rm -f /etc/ssh/ssh_host_*_key*

RUN mkdir /helpers
COPY copy_ssh_keys.py /helpers
RUN mkdir -p ~/.ssh/

EXPOSE 22
################## END SSH STUFF ##################

################# BEGIN SUPERVISORD STUFF #################
# SUPERVISORD for managing multiple processes inside one docker container
RUN apt-get install -y supervisor
COPY supervisord.conf /etc/supervisord.conf
RUN mkdir -p /var/log/supervisor
################## END SUPERVISORD STUFF ##################

################# BEGIN TESTING STUFF #################
## This is for testing.  Create a local directory of ssh keys.
#RUN mkdir -p /secrets/
#COPY ./ssh_keys_for_testing/ /secrets/
#RUN ls -la /secrets/
#RUN ls -la /secrets/ssh-server-keys
#RUN ls -la /secrets/user-keys
#RUN ls -la /secrets/user-login-public-keys
################## END TESTING STUFF ##################

################## BEGIN REPO STUFF ##################
## enable downloading from github
## ref: https://stackoverflow.com/questions/40469380/docker-how-to-deal-with-ssh-keys-known-hosts-and-authorized-keys
## TODO: do we need other services here?
RUN touch ~/.ssh/known_hosts
RUN ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts
RUN ssh-keyscan -t rsa gitlab.com >> ~/.ssh/known_hosts
RUN ssh-keyscan -t rsa bitbucket.com >> ~/.ssh/known_hosts
################### END REPO STUFF ###################

################# BEGIN PYTHON STUFF #################
RUN pip install ipython pandas scikit-learn keras google-cloud-storage cloudml-hypertune Flask gunicorn
################## END PYTHON STUFF ##################

################# BEGIN WEB SERVER STUFF #################
WORKDIR /app
COPY . .
EXPOSE 80
################## END WEB SERVER STUFF ##################

CMD python /helpers/copy_ssh_keys.py --ssh_server_keys_mountpoint=/secrets/ssh-server-keys --user_keys_mountpoint=/secrets/user-keys --user_login_public_keys_mountpoint=/secrets/user-login-public-keys && /usr/bin/supervisord -c /etc/supervisord.conf
