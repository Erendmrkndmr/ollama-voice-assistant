FROM jenkins/jenkins:lts

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg lsb-release git \
 && rm -rf /var/lib/apt/lists/*

# Docker CLI + compose plugin
RUN mkdir -p /usr/local/lib/docker/cli-plugins \
 && curl -fsSL https://download.docker.com/linux/static/stable/$(uname -m)/docker-24.0.9.tgz \
    | tar xz -C /usr/local/bin --strip=1 docker/docker \
 && curl -fsSL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-$(uname -m) \
    -o /usr/local/lib/docker/cli-plugins/docker-compose \
 && chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

USER jenkins

# Plugin’leri bir dosyadan, sürümsüz (son sürüm) kur
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# JCasC
COPY casc.yaml /usr/share/jenkins/ref/casc.yaml
ENV CASC_JENKINS_CONFIG=/usr/share/jenkins/ref/casc.yaml
