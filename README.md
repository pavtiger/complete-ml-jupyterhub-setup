# complete-ml-jupyterhub-setup
My favourite way to setup jupyterhub for ML: auth via GitHub, docker launcher with a separate direcrory for files


## Configuring
Copy `config.py.example` to `config.py` and change fields.

Build source docker container for jupyter
```shell
cd docker-jupyter-cuda
make build/pytorch-notebook-cuda
```

Build the template image for each user
```shell
docker build -t jupyter_custom_notebook -f template.Dockerfile .
# with version
docker build --build-arg BASE_VERSION=cuda12.4.1-cudnn-devel-ubuntu22.04-py3.10 -t jupyter_custom_notebook:cuda12.4.1-cudnn-devel-ubuntu22.04-py3.10 -f template.Dockerfile .
```


Build the juputerhub image itself
```shell
docker build -t pavtiger/jupyterhub .

```

If you make any changes to the template image, you can rebuild it and remove the previous user container. On new hub initialization jupyterhub will use the updated template

