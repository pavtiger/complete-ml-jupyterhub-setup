c = get_config()

from dockerspawner import DockerSpawner
import os, yaml
import re
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
DATASETS_ROOT = "/mnt/shuttle/datasets"          # host path with all datasets
DATASETS_MOUNT_ROOT = "/workdir/datasets"        # path inside user containers
WORKDIR_MOUNT_ROOT = "/workdir"
USER_DATASETS_FILE = "/srv/jupyterhub/configs/user_config.yml"

c.DockerSpawner.allowed_images = {
    "(default) cuda12.4.1-cudnn-devel-ubuntu22.04-torch2.5.1-py3.11": "jupyter_custom_notebook:cuda12.4.1-cudnn-devel-ubuntu22.04-torch2.5.1-py3.11",
    "cuda11.8.0-cudnn8-devel-ubuntu22.04-torch2.2.2-py3.9": "jupyter_custom_notebook:cuda11.8.0-cudnn8-devel-ubuntu22.04-torch2.2.2-py3.9",
    "cuda11.1.1-cudnn8-devel-ubuntu20.04-torch1.10.1-py3.8": "jupyter_custom_notebook:cuda11.1.1-cudnn8-devel-ubuntu20.04-torch1.10.1-py3.8",
    "cuda11.8.0-cudnn8-devel-ubuntu22.04-torch2.4.0-py3.9": "jupyter_custom_notebook:cuda11.8.0-cudnn8-devel-ubuntu22.04-torch2.4.0-py3.9",
#    "cadrille": "cadrille"
}
c.DockerSpawner.default_url = "/lab"
c.DockerSpawner.network_name = 'jupyterhub'
c.DockerSpawner.notebook_dir = '/workdir'
c.DockerSpawner.extra_host_config = {
    "shm_size": "16g"
}
# c.DockerSpawner.environment = {
#     'NVIDIA_VISIBLE_DEVICES': '0,1'
# }

# we need the hub to listen on all ips when it is in a container
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_port = 8888
c.Spawner.start_timeout = 1000
c.DockerSpawner.remove = False

# Docker options (modify as per your requirements)
c.DockerSpawner.extra_create_kwargs.update({
    'user': 'root',  # Ensure root user can set permissions
})


_slug_re = re.compile(r'[^a-zA-Z0-9_.-]+')  # allowed by Docker names

def _slug(s: str, maxlen=80) -> str:
    s = _slug_re.sub('_', s)
    s = s.strip('_.-')
    return (s or 'image')[:maxlen]

class ImageNamedDockerSpawner(DockerSpawner):
    def template_namespace(self):
        ns = super().template_namespace()
        img = getattr(self, "image", "") or ""
        tag = img.split(":")[-1] if ":" in img else img
        ns.update({
            "image_tag": _slug(tag),   # e.g. cuda12_4_1_cudnn_devel_ubuntu22_04_torch2_5_1_py3_11
            "image_full": _slug(img),  # full image ref if you ever want it
        })
        return ns


c.JupyterHub.spawner_class = ImageNamedDockerSpawner

# If you use named servers (you do), include {servername} for uniqueness
c.DockerSpawner.container_name_template = "jupyter-{username}-{servername}-{image_tag}"

# c.DockerSpawner.container_name_template = name_template

def _load_user_config():
    """
    Returns {username: [relative_dataset_paths,...]}.
    Unknown/missing file -> {}.
    """
    try:
        with open(USER_DATASETS_FILE, "r") as f:
            cfg = yaml.safe_load(f) or {}
        return (cfg.get("users") or {})
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"[datasets] failed to read {USER_DATASETS_FILE}: {e}")
        return {}

def _safe_under(base: str, rel: str) -> str | None:
    """
    Join and ensure the result stays under `base` (guards against .. traversal).
    """
    p = os.path.normpath(os.path.join(base, rel))
    return p if os.path.commonpath([base, p]) == os.path.normpath(base) else None


def create_dir_hook(spawner):
    username = spawner.user.name
    home_p = os.path.join('/workdir', "homes", username)
    if not os.path.exists(home_p):
        os.mkdir(home_p, 0o755)
        os.mkdir(os.path.join(home_p, ".ssh"), 0o755)

    container_path = os.path.join('/workdir', username)
    if not os.path.exists(container_path):
        os.mkdir(container_path, 0o755)

    inside_workdir_path = os.path.join('/workdir', username, "workdir")
    if not os.path.exists(inside_workdir_path):
        os.mkdir(inside_workdir_path, 0o755)

    home_folders = os.listdir(home_p)

    # Main volume mapping
    volume_mapping = {}

    # Add shared conda mount
    conda_path = "/opt/anaconda3"
    volume_mapping[conda_path] = os.path.join("/home/jovyan", "anaconda3")

    cfg = _load_user_config()
    user_cfg = cfg.get(username, {}) or {}

    # --- GPU Configuration ---
    gpu_ids = user_cfg.get("gpus", [])
    
    if gpu_ids:
        # Convert list to comma-separated string (e.g., ["0", "1"] -> "0,1")
        gpu_string = ",".join(str(g) for g in gpu_ids)
        
        # Set environment variable to restrict visible GPUs
        spawner.environment["NVIDIA_VISIBLE_DEVICES"] = gpu_string
        
        # Use device_requests for modern Docker GPU support
        from docker.types import DeviceRequest
        spawner.extra_host_config["device_requests"] = [
            DeviceRequest(
                device_ids=gpu_ids,
                capabilities=[["gpu"]]
            )
        ]
    else:
        # No GPUs assigned - disable GPU access entirely
        spawner.environment["NVIDIA_VISIBLE_DEVICES"] = ""
        spawner.extra_host_config.pop("device_requests", None)

    # --- Teams/workdir mounts ---
    requested = user_cfg.get("teams", [])
    for rel_ds in requested:
        host_ds = _safe_under(WORKDIR_PATH, rel_ds)
        if not host_ds:
            print(f"[teams] skipped unsafe path '{rel_ds}' for {username}")
            continue
        container_target = os.path.join(WORKDIR_MOUNT_ROOT, rel_ds)
        volume_mapping[host_ds] = container_target

    # --- Dataset mounts ---
    requested = user_cfg.get("datasets", [])
    for rel_ds in requested:
        host_ds = _safe_under(DATASETS_ROOT, rel_ds)
        if not host_ds:
            print(f"[datasets] skipped unsafe path '{rel_ds}' for {username}")
            continue
        if not os.path.isdir(host_ds):
            print(f"[datasets] missing on host: {host_ds} (user {username})")
            continue
        container_target = os.path.join(DATASETS_MOUNT_ROOT, rel_ds)
        volume_mapping[host_ds] = container_target

    # --- Home directory mounts ---
    for home_folder in home_folders:
        home_path = os.path.join(WORKDIR_PATH, "homes", username, home_folder)
        volume_mapping[home_path] = os.path.join("/home/jovyan", home_folder)

    print(f"[GPU] User {username} assigned GPUs: {gpu_ids}", flush=True)
    print("VOLUME_MAPPING", volume_mapping, flush=True)
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

