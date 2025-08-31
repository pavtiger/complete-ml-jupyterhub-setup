# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
FROM pavtiger/pytorch-notebook-cuda:cuda12.2.2-cudnn8-devel-ubuntu22.04-py3.10

LABEL maintainer="Jupyter Project <jupyter@googlegroups.com>"
USER root

# Custom
RUN apt update && apt upgrade -y
RUN apt install vim unzip wget iproute2 -y
RUN apt install openssh-server wget curl vim git htop nvtop python3 python3-pip iproute2 zsh byobu sudo -y

RUN pip3 install wandb scikit-learn pandas tqdm torch tensorflow tensorboard torchvision opencv-python matplotlib seaborn scipy lightgbm gdown transformers

# fix YOLO
RUN apt install ffmpeg libsm6 libxext6 -y

# Fix extensions
# chown -R pavtiger:pavtiger /usr/local/share/jupyter/
RUN pip3 install jupyter_scheduler jupyterlab-git

# Themes and plugins:
RUN pip3 install jupyterlab_materialdarker theme-darcula
 # jupyterlab_latex jupyterlab-spellchecker

# LaTex
RUN apt-get install texlive-xetex texlive-lang-cyrillic -y  # Russian

# Build pytorch3d
# RUN pip install "git+https://github.com/facebookresearch/pytorch3d.git"
RUN pip install open3d

RUN echo "$NB_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/notebook
WORKDIR /workdir

# Save all library versions
RUN pip freeze > /requirements.txt

