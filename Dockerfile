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
#RUN sed -i 's/self\._useragent\ \=\ None/self._useragent = str\(\"Jon Heese\"\)/' /usr/local/lib/python3.8/site-packages/pymyq/request.py
#RUN wget https://github.com/Lash-L/pymyq/archive/refs/heads/useragent_fix.zip && \
#    unzip useragent_fix.zip && \
#    rm -rf /usr/local/lib/python3.8/site-packages/pymyq && \
#    mv pymyq-useragent_fix/pymyq /usr/local/lib/python3.8/site-packages/ && \
#    rm -rf useragent_fix.zip pymyq-useragent_fix
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
CMD ["python3", "robot.py"]
