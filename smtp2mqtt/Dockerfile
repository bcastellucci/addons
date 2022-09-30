ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app

COPY start.sh smtp2mqtt.py /app/

RUN apk add --no-cache python3 py3-pip && pip3 install paho-mqtt aiosmtpd

ENTRYPOINT ["/app/start.sh"]

LABEL \
  io.hass.version="VERSION" \
  io.hass.type="addon" \
  io.hass.arch="armhf|aarch64|i386|amd64"
