FROM jupyterhub/jupyterhub

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y vim unzip wget iproute2 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


RUN pip3 install notebook jupyterlab jupyterhub==5.2.0 jupyterhub-nativeauthenticator oauthenticator

# Fix extensions
RUN pip3 install jupyter_scheduler jupyterlab-git dockerspawner

# Themes and plugins:
RUN pip3 install jupyterlab_materialdarker theme-darcula jupyterlab_latex jupyterlab-spellchecker

# LaTex
# RUN apt-get install texlive-xetex texlive-lang-cyrillic -y  # Russian

COPY config.py /srv/jupyterhub/custom_config.py
COPY user_config.yml /srv/jupyterhub/user_config.yml
COPY jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]

