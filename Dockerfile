# Container image that runs your code
FROM python:3.11-slim

# Instalando as dependencias
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY entrypoint.sh /entrypoint.sh
COPY main.py /main.py
COPY chat.py /chat.py

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/entrypoint.sh"]
