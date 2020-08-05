FROM python:alpine3.12

RUN apk add --no-cache --virtual build-dependencies \
      build-base \
      linux-headers \
    && apk add --no-cache \
      supervisor \
    && pip install --upgrade \
      pip \
      metrics2mqtt==0.1.14 \
    && apk del build-dependencies

# Copy configuration files:
COPY supervisor.conf /etc/supervisor.conf
COPY run.sh /usr/local/bin/run.sh

# Run:
ENTRYPOINT ["/usr/local/bin/run.sh"]
