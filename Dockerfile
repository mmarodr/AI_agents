FROM registry.petrobras.com.br/imagens-devops/base/petro-python3.10-slim:latest

ARG PORT=5000

ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL "en_US.UTF-8"
ENV LANG "en_US.UTF-8"
ENV LANGUAGE "en_US.UTF-8"
ENV PIP_DEFAULT_TIMEOUT 10000
ENV PYTHONUNBUFFERED 1
# ENV PYTHONPATH="/var/www/app:$PYTHONPATH"

COPY ./servicoca-petrobras-com-br-chain.pem app/
COPY ./certs/* app/certs/
COPY ./requirements.txt app/

RUN apt update && apt -y upgrade \
    && apt install tzdata -y \
    && update-ca-certificates -v \
    && dpkg-reconfigure -f noninteractive tzdata && \
    apt-get install -y locales && \
    echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen && \
    apt-get install -y gcc apache2 apache2-dev python3-dev libc-dev libpython3-dev libapache2-mod-wsgi-py3 libxml2 libxml2-dev libxslt-dev unzip libaio1 && \
    apt-get autoremove -y && \
    apt-get clean -y

RUN python -m pip install --upgrade pip && \
    pip install -r /app/requirements.txt && \
    pip cache purge

#copiando os arquivos
COPY ./Petrobras_AI_Agents /var/www/app/Petrobras_AI_Agents
COPY ./config_json /var/www/app/config_json

COPY . /var/www/app/

RUN cat /app/servicoca-petrobras-com-br-chain.pem >> /usr/local/lib/python3.10/site-packages/certifi/cacert.pem

ARG LD_LIBRARY_PATH=/opt/oracle/instantclient
ARG APP_NAME=/var/www/app/app.py
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}
ENV FLASK_APP=${APP_NAME}


# ================= WSGI
WORKDIR /var/www/app/

EXPOSE ${PORT}


CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]