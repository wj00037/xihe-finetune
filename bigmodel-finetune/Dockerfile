FROM ubuntu:20.04

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y && \
    apt-get install -y python3.9 python3-pip python3.9-dev

EXPOSE 8080

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# RUN apt install systemctl 2> /dev/null && apt install haveged -y  2> /dev/null && systemctl start haveged && systemctl enable haveged.service
COPY script /script
WORKDIR /script

ADD  https://temp-data.obs.cn-central-221.ovaijisuan.com:443/xihe-finetune/Ascend_mindxsdk_mxFoundationModel-1.0.1.RC2.b001-py3-none-any.whl Ascend_mindxsdk_mxFoundationModel-1.0.1.RC2.b001-py3-none-any.whl
ADD  https://temp-data.obs.cn-central-221.ovaijisuan.com:443/xihe-finetune/modelarts-latest-py2.py3-none-any.whl modelarts-latest-py2.py3-none-any.whl

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Install finetune requrements
RUN bash fm_user.sh uninstall fm
RUN bash fm_user.sh uninstall ma
RUN bash fm_user.sh install fm
RUN bash fm_user.sh install ma

COPY . /bigmodel-finetune
WORKDIR /bigmodel-finetune

RUN pip install -r requirements.txt

RUN mkdir -p /bigmodel-finetune/test && cp requirements.txt /bigmodel-finetune/test
RUN adduser -u 5000 --disabled-password --gecos "" mindspore && chown -R mindspore /bigmodel-finetune && chmod -R 755 /usr/local/lib/python3.8

USER mindspore

CMD ["gunicorn", "-c", "gunicorn.config.py", "app.run:app"]
