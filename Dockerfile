FROM jupyterhub/jupyterhub

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y vim unzip wget iproute2 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


RUN pip3 install notebook jupyterlab jupyterhub==5.2.0 jupyterhub-nativeauthenticator oauthenticator
# RUN pip3 install wandb scikit-learn pandas tqdm torch tensorboard torchvision opencv-python matplotlib seaborn scipy

# fix YOLO
# RUN apt install ffmpeg -y # libsm6 libxext6 -y
# pip install numpy==1.21.2

# Fix extensions
# chown -R pavtiger:pavtiger /usr/local/share/jupyter/
RUN pip3 install jupyter_scheduler jupyterlab-git dockerspawner

# Themes and plugins:
RUN pip3 install jupyterlab_materialdarker theme-darcula jupyterlab_latex jupyterlab-spellchecker

# LaTex
# RUN apt-get install texlive-xetex texlive-lang-cyrillic -y  # Russian

#COPY welcome.ipynb 
COPY config.py /srv/jupyterhub/custom_config.py
COPY jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]

