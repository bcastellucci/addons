#!/usr/bin/env python3
import asyncio
import email
import logging
import os
import signal
import time
import json
import base64
import smtplib
import uuid
from email.policy import default
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult
from paho.mqtt import publish

##
## Original source from https://github.com/wicol/emqtt
##

defaults = {
    "SMTP_LISTEN_PORT": "25",
    "SMTP_AUTH_REQUIRED": "False",
    "SMTP_RELAY_HOST": None,
    "SMTP_RELAY_PORT": None,
    "SMTP_RELAY_USER": None,
    "SMTP_RELAY_PASS": None,
    "SMTP_RELAY_STARTTLS": None,
    "SMTP_RELAY_TIMEOUT_SECS": None,
    "MQTT_HOST": "localhost",
    "MQTT_PORT": None,
    "MQTT_USER": None,
    "MQTT_PASS": None,
    "MQTT_TOPIC": "smtp2mqtt",
    "PUBLISH_ATTACHMENTS": "False",
    "SAVE_ATTACHMENTS_DIR": None,
    "DEBUG": "False",
}
config = {
    setting: os.environ.get(setting, default) for setting, default in defaults.items()
}
# Boolify
for key, value in config.items():
    if (value and value.lower() == "true"):
        config[key] = True
    elif (value and value.lower() == "false"):
        config[key] = False

level = logging.DEBUG if config["DEBUG"] else logging.INFO

log = logging.getLogger("smtp2mqtt")
log.setLevel(level)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(uuid)s - %(message)s")

# Log to console
ch = logging.StreamHandler()
ch.setFormatter(formatter)
log.addHandler(ch)


class SMTP2MQTTHandler:
    def __init__(self, loop):
        self.loop = loop
        self.quit = False
        signal.signal(signal.SIGTERM, self.set_quit)
        signal.signal(signal.SIGINT, self.set_quit)

    async def handle_DATA(self, server, session, envelope):
        log_extra = {'uuid': str(uuid.uuid4())[:8]}
        log.info("Message from %s", envelope.mail_from, extra=log_extra)
        if (log.isEnabledFor(logging.DEBUG)):
            log.debug("Message data (truncated): %s", envelope.content.decode("utf8", errors="replace")[:500], extra=log_extra)

        # extract the message as an email.message.Message object
        msg = email.message_from_bytes(envelope.original_content, policy=default)

        # topic based on sender
        topic = "{}/{}".format(
            config["MQTT_TOPIC"], envelope.mail_from.replace("/", "")
        )
        
        # payload is split into two - headers and mime_parts
        payload = {'uuid': log_extra['uuid'], 'headers': {}, 'mime_parts': []}

        # add all the headers to the payload (normalize the header name to lower-case)
        # *we're ignoring that one header may have multiple values, technically we're going
        # to overwrite successively, but it's ok, we're not really that picky about the headers...
        for header in msg.items():
            payload['headers'][header[0].lower()] = header[1]
            if (log.isEnabledFor(logging.DEBUG)): log.debug("got message header %s: %s", header[0], header[1], extra=log_extra)
        
        #get the message body
        msgBody = msg.get_body()
        mime_part = {'best_guess': 'message body', 'headers': {}}
        # headers (same deal as above)
        for header in msgBody.items():
            mime_part['headers'][header[0].lower()] = header[1]
            if (log.isEnabledFor(logging.DEBUG)): log.debug("got body header %s: %s", header[0], header[1], extra=log_extra)
        mime_part['content'] = msgBody.get_content()
        if (log.isEnabledFor(logging.DEBUG)): log.debug("stored [%s] as the content", mime_part['content'], extra=log_extra)
        payload['mime_parts'].append(mime_part)

        # get the attachments next
        for attachment in msg.iter_attachments():
            mime_part = {'best_guess': 'attachment', 'headers': {}}
            # headers (same deal as above)
            for header in attachment.items():
                mime_part['headers'][header[0].lower()] = header[1]
                if (log.isEnabledFor(logging.DEBUG)): log.debug("got attachment header %s: %s", header[0], header[1], extra=log_extra)
            # only include the data if configured to!
            if (config["PUBLISH_ATTACHMENTS"]):
                # encode it as base64. Even though it is already encoded in some manner and
                # the content-type and content-transfer-encoding headers would tell someone how
                # to decode it, it is courteous to just normalize it to one, specific, well-known
                # encoding and be done with it.
                mime_part['content'] = base64.b64encode(attachment.get_content()).decode("utf8", errors="replace")
                if (log.isEnabledFor(logging.DEBUG)): log.debug("stored [%s] as the content", mime_part['content'], extra=log_extra)
            else:
                log.debug("SKIP publish attachment data", extra=log_extra)
                mime_part['content'] = "<not configured to publish attachment data>"
            # save the attachment, if we are supposed to
            if (config["SAVE_ATTACHMENTS_DIR"]):
                filename = f"{log_extra['uuid']}_{attachment.get_filename()}"
                file_path = os.path.join(config["SAVE_ATTACHMENTS_DIR"], filename)
                log.info("Saving attachment to %s", file_path, extra=log_extra)
                with open(file_path, "wb") as f:
                    f.write(attachment.get_content())
                # note the file name in the payload
                mime_part['saved_file_name'] = file_path
            else:
                log.debug("SKIP saving attachment data to a file", extra=log_extra)
        payload['mime_parts'].append(mime_part)

        # publish
        self.mqtt_publish(topic, json.dumps(payload), log_extra)

        # go ahead & send the original message on its way (if configured to)
        if (config["SMTP_RELAY_HOST"]):
            self.smtp_relay(msg, envelope.mail_from, envelope.rcpt_tos, log_extra)
        else:
            log.debug("SKIP relaying the original email", extra=log_extra)

        # done!
        return "250 Message accepted for delivery"

    def mqtt_publish(self, topic, payload, log_extra):
        if config["DEBUG"]:
            if (log.isEnabledFor(logging.DEBUG)): log.debug('Publishing [%s] to %s', payload, topic, extra=log_extra)
        else:
            log.info('Publishing to %s', topic, extra=log_extra)
        try:
            publish.single(
                topic,
                payload,
                hostname=config["MQTT_HOST"],
                port=int(config["MQTT_PORT"]) if config["MQTT_PORT"] else 1883,
                auth={
                    "username": config["MQTT_USER"],
                    "password": config["MQTT_PASS"],
                }
                if config["MQTT_USER"]
                else None,
            )
        except Exception as e:
            log.exception("Failed publishing", extra=log_extra)
    
    def smtp_relay(self, msg, mail_from, rcpt_tos, log_extra):
        log.info("Relaying the original email", extra=log_extra)
        with smtplib.SMTP(
            host=config["SMTP_RELAY_HOST"],
            port=int(config["SMTP_RELAY_PORT"]) if config["SMTP_RELAY_PORT"] else 25,
            timeout=int(config["SMTP_RELAY_TIMEOUT_SECS"]) if config["SMTP_RELAY_TIMEOUT_SECS"] else 10
        ) as relay:
            try:
                if (config["SMTP_RELAY_STARTTLS"]):
                    relay.starttls()
                    relay.ehlo()
                if (config["SMTP_RELAY_USER"]):
                    relay.login(user=config["SMTP_RELAY_USER"], password=config["SMTP_RELAY_PASS"])
                relay.send_message(msg, mail_from, rcpt_tos)
            except Exception as e:
                log.exception("Failed relaying", extra=log_extra)

    def set_quit(self, *args):
        log.info("Quitting...", extra={'uuid': 'main thread'})
        self.quit = True

def dummy_auth_function(server, session, envelope, mechanism, auth_data):
    log.info("dummy-authenticating whatever credentials are offered...", extra={'uuid': 'main thread'})
    return AuthResult(success=True)


if __name__ == "__main__":
    if (log.isEnabledFor(logging.DEBUG)):
        log.debug(", ".join([f"{k}={v}" for k, v in config.items()]), extra={'uuid': 'main thread'})

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    c = Controller(
        handler=SMTP2MQTTHandler(loop),
        loop=loop,
        hostname="0.0.0.0",
        port=int(config["SMTP_LISTEN_PORT"]),
        authenticator=dummy_auth_function,
        auth_required=config["SMTP_AUTH_REQUIRED"],
        #quite down the warnings when auth-required is false by letting this be true (we won't use it anyway, doesn't hurt to be true)...
        auth_require_tls=(not config["SMTP_AUTH_REQUIRED"]),
    )
    c.start()
    log.info("Running", extra={'uuid': 'main thread'})
    try:
        while not c.handler.quit:
            time.sleep(0.5)
        c.stop()
    except:
        c.stop()
        raise
