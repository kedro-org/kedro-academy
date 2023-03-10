FROM gitpod/workspace-python-3.10:2023-03-06-18-43-51

RUN pyenv uninstall -f 3.10.9 || true \
    && pyenv install mambaforge-22.9.0-2 \
    && pyenv global mambaforge-22.9.0-2
