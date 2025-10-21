# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

ARG BASE_VERSION=cuda12.2.2-cudnn8-devel-ubuntu22.04-py3.10
FROM pavtiger/pytorch-notebook-cuda:${BASE_VERSION}

LABEL maintainer="Jupyter Project <jupyter@googlegroups.com>"
USER root

# Custom
RUN set -eux; \
    for f in /etc/apt/sources.list.d/*cuda* /etc/apt/sources.list.d/*nvidia*; do \
      [ -e "$f" ] && mv "$f" "$f.disabled"; \
    done; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      vim unzip wget iproute2 openssh-server curl git htop nvtop python3 python3-pip zsh byobu sudo; \
    rm -rf /var/lib/apt/lists/*
# RUN apt update && apt upgrade -y
RUN apt install vim unzip wget iproute2 -y  # Helpful linux commands
RUN apt install openssh-server wget curl vim git htop nvtop python3 python3-pip iproute2 zsh byobu sudo -y

# RUN pip3 install wandb scikit-learn pandas tqdm torch tensorflow tensorboard torchvision opencv-python matplotlib seaborn scipy lightgbm gdown transformers

# fix YOLO
RUN apt install ffmpeg libsm6 libxext6 -y

# Fix extensions
RUN pip3 install jupyter_scheduler jupyterlab-git

# Themes and plugins:
RUN pip3 install jupyterlab_materialdarker theme-darcula jupyterlab_latex jupyterlab-spellchecker

RUN pip3 install --no-cache-dir sqlalchemy==1.4.52

# LaTex
# RUN apt-get install texlive-xetex texlive-lang-cyrillic -y  # Russian
# Build pytorch3d
# RUN pip install "git+https://github.com/facebookresearch/pytorch3d.git"
# RUN pip install open3d

# jovyan user setup
ARG NB_USER=jovyan
RUN apt-get update && apt-get install -y --no-install-recommends sudo && \
    echo "${NB_USER} ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/notebook && \
    chmod 0440 /etc/sudoers.d/notebook

# RUN echo "$NB_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/notebook
WORKDIR /workdir

# Save all library versions
RUN pip freeze > /requirements.txt

