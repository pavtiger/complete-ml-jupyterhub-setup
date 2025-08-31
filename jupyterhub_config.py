c = get_config()

from dockerspawner import DockerSpawner
import os
import sys
import shutil
from jupyterhub.auth import PAMAuthenticator
from jupyterhub.spawner import Spawner

# Load parameters from config file
sys.path.insert(0, os.path.dirname(__file__))
from custom_config import WORKDIR_PATH, ALLOWED_USERS, ADMIN_USERS, TEMPLATE_PATH


# Specify Docker Spawner
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'

# The docker instances need access to the Hub, so the default loopback port doesn't work:
from jupyter_client.localinterfaces import public_ips
c.JupyterHub.hub_ip = public_ips()[0]

# Set the Docker image to be used for user containers (prebuilt in this repository)
c.DockerSpawner.image = 'jupyter_custom_notebook'
c.DockerSpawner.default_url = "/lab"
c.DockerSpawner.network_name = 'jupyterhub'
c.DockerSpawner.notebook_dir = '/workdir'
c.DockerSpawner.extra_host_config = {
    'runtime': 'nvidia',
    "shm_size": "16g",
	"port_bindings": {
        6006: 6006
    }
}

# we need the hub to listen on all ips when it is in a container
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_port = 8888
c.Spawner.start_timeout = 1000

# Automatically create home directories for each user
c.DockerSpawner.remove = False

# Docker options (modify as per your requirements)
c.DockerSpawner.extra_create_kwargs.update({
    'user': 'root',  # Ensure root user can set permissions
})


def create_dir_hook(spawner):
    username = spawner.user.name # get the username
    user_path = os.path.join(WORKDIR_PATH, username, "workdir")
    home_p = os.path.join('/workdir', username, "home")

    # Create a user dir from host connected to the main container
    container_path = os.path.join('/workdir', username)
    if not os.path.exists(container_path):
        # create a directory with umask 0755 
        # hub and container user must have the same UID to be writeable
        # still readable by other users on the system
        os.mkdir(container_path, 0o755)

    inside_workdir_path = os.path.join('/workdir', username, "workdir")
    if not os.path.exists(inside_workdir_path):
        os.mkdir(inside_workdir_path, 0o755)

    inside_home_path = os.path.join('/workdir', username, "home")
    if not os.path.exists(inside_home_path):
        os.mkdir(inside_home_path, 0o755)

    # copy template to the user directory
    shutil.copy(os.path.join('/workdir', TEMPLATE_PATH), os.path.join(container_path, TEMPLATE_PATH))

    home_folders = os.listdir(home_p)
    print(home_folders)
    # Main volume mapping
    # volume_mapping = {
    #     user_path : '/workdir'
    # }
    shared_path = os.path.join(WORKDIR_PATH, "shared")
    volume_mapping = {
        shared_path : '/workdir'
    }
    # for home_folder in home_folders:  # Add custom user mounts to /home/jovyan
    #     home_path = os.path.join(WORKDIR_PATH, username, "home", home_folder)
    #     volume_mapping[home_path] = os.path.join("/home/jovyan", home_folder)

    # Add shared conda mount (on the host)
    conda_path = "/opt/anaconda3"
    volume_mapping[conda_path] = os.path.join("/home/jovyan", "anaconda3")

    # Add shared workdir (on NAS via NFS)
    # shared_path = os.path.join('/workdir', "shared")
    # volume_mapping[shared_path] = "/workdir/shared"

    print(volume_mapping)
    spawner.volumes = volume_mapping


c.DockerSpawner.pre_spawn_hook = create_dir_hook



import os
pjoin = os.path.join

runtime_dir = os.path.join('/srv/jupyterhub')
ssl_dir = pjoin(runtime_dir, 'ssl')

# Allows multiple single-server per user
c.JupyterHub.allow_named_servers = True

# put the JupyterHub cookie secret and state db
# in /var/run/jupyterhub
c.JupyterHub.cookie_secret_file = pjoin(runtime_dir, 'cookie_secret')
c.JupyterHub.db_url = pjoin(runtime_dir, 'jupyterhub.sqlite')

# use GitHub OAuthenticator for local users
c.JupyterHub.authenticator_class = 'oauthenticator.LocalGitHubOAuthenticator'
c.GitHubOAuthenticator.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']

# create system users that don't exist yet
c.LocalAuthenticator.create_system_users = True

# specify users and admin
c.Authenticator.allow_existing_users = True
c.Authenticator.allowed_users = ALLOWED_USERS
c.Authenticator.admin_users = ADMIN_USERS

# c.Spawner.args = ['--NotebookApp.default_url=/welcome.ipynb']

