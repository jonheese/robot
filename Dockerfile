FROM python:3.8.2-alpine
WORKDIR /usr/src/app
RUN pip install --upgrade pip
RUN apk add --no-cache --virtual .build-deps build-base libffi-dev
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install --upgrade pip
RUN set -eux\
    && pip install -r /usr/src/app/requirements.txt \
    && rm -rf /root/.cache/pip
COPY . /usr/src/app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
CMD ["python3", "robot.py"]
