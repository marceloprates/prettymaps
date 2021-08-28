# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.191.1/containers/python-3/.devcontainer/base.Dockerfile

# [Choice] Python version: 3, 3.9, 3.8, 3.7, 3.6
ARG VARIANT="3.9"
FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}

# vsketch as of Aug 25, 2021
RUN pip3 --disable-pip-version-check --no-cache-dir install https://github.com/abey79/vsketch/archive/6d4b4ea1de27ba563032ce1aee02457c16d4ea60.zip
