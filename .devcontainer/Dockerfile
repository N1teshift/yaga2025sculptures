FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl gnupg2 software-properties-common && rm -rf /var/lib/apt/lists/*

# Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get update && apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*

# Install system packages mirroring the control node and Pi simulator
RUN apt-get update && apt-get install -y \
    icecast2 \
    liquidsoap \
    mosquitto \
    mosquitto-clients \
    darkice \
    mpv \
    python3-paho-mqtt \
    python3-pip \
    iproute2 \
    net-tools \
    openssh-server \
    ffmpeg \
    pulseaudio \
    pulseaudio-utils \
    alsa-utils \
    alsa-oss \
    libasound2-plugins \
    nano \
    htop \
    sudo && rm -rf /var/lib/apt/lists/*

RUN npm install -g node-red

COPY server/liquidsoap/requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Create vscode user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME && \
    useradd --uid $USER_UID --gid $USER_GID -m $USERNAME && \
    echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME
WORKDIR /workspace
