#!/usr/bin/env bashio

bashio::log.info "getting configuration..."
CONFIG_PATH=/data/options.json

#grab this first since we'll use it below
DEBUG="$(bashio::config 'debug')"
if [[ -n $DEBUG ]] && [[ $DEBUG != "null" ]]; then
    if [[ $DEBUG = "true" ]]; then
        bashio::log.info "exporting [DEBUG=${DEBUG}]"
    fi
    export DEBUG
fi

#treat this as special
MQTT_HOST="$(bashio::config 'mqtt_host' 'core-mosquitto')"
if [[ $DEBUG = "true" ]]; then
    bashio::log.info "exporting [MQTT_HOST=$MQTT_HOST]"
fi
export MQTT_HOST=$MQTT_HOST

#grab the rest in a loop
for var in \
    smtp_relay_host smtp_relay_port smtp_relay_user smtp_relay_pass smtp_relay_starttls smtp_relay_timeout_secs \
    mqtt_port mqtt_user mqtt_pass mqtt_topic \
    publish_attachments \
;
do
    v="$(bashio::config ${var})"
    if [[ -n $v ]] && [[ $v != "null" ]]; then
        if [[ $DEBUG = "true" ]]; then
            bashio::log.info "exporting [${var^^}=${v}]"
        fi
        export ${var^^}=${v}
    fi
done

#create a sub directory under share
SAVE_ATTACHMENTS="$(bashio::config 'save_attachments')"
if [[ -n $SAVE_ATTACHMENTS ]] && [[ ${SAVE_ATTACHMENTS,,} = "true" ]]; then
    SAVE_ATTACHMENTS_DIR="/share/smtp2mqtt"
    if [[ -n ${MQTT_TOPIC:-} ]] && [[ $MQTT_TOPIC != "null" ]]; then
        SAVE_ATTACHMENTS_DIR="/share/$MQTT_TOPIC"
    fi
    if [[ $DEBUG = "true" ]]; then
        bashio::log.info "creating attachment save dir $SAVE_ATTACHMENTS_DIR"
    fi
    mkdir -p $SAVE_ATTACHMENTS_DIR
    if [[ $DEBUG = "true" ]]; then
        bashio::log.info "exporting [SAVE_ATTACHMENTS_DIR=${SAVE_ATTACHMENTS_DIR}]"
    fi
    export SAVE_ATTACHMENTS_DIR
fi

bashio::log.info "starting application..."
python3 /app/smtp2mqtt.py
