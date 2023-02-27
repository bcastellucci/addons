# Home Assistant Add-on: SMTP2MQTT

Turns Home Assistent into an SMTP server, publishes messages (email) to an MQTT broker.

*The original source for this came from the [wicol/emqtt] project on github

## How to use

The add-on strives to have sensible defaults, some assumptions it makes and things that may need tweaked (click 'Show unused optional configuration options' on the Configuration page to see these) are:

1. It is assumed the intent is to use the Mosquitto broker add-on and it is already installed in a Supervised Home Assistant instance. If this is the case the add-on can simply be started without any additional configuration (caveat #2 below). If this is not the case then the MQTT Host will have to be set accordingly (along with the port, if not the default 1883).
2. Unless the MQTT broker allows anonymous connections/publishing, an MQTT username and password will need to be set, consult the MQTT broker configuration.
3. By default, the add-on will not publish attachment data to MQTT nor will it save attachment data to the file system. One or both of these options may be turned on.
4. There are other options that should be self-explanatory (they are described in detail below).
5. Once all desired options have been set go ahead and start the add-on, it takes a few seconds to start up. Check the add-on log output to see the result.

## Finer Details

This add-on will publish the entire email, in JSON format.

- There will be a `uuid` attribute in every payload published.
- Headers will be turned into a JSON object under the key `headers`, with attributes where the header name is the attribute and the header value is, well, the value (this ignores that a header may have multiple values, which is arguably rare, in which case the last value wins).
- All MIME parts will be published as JSON objects, in an array under the key `mime_parts`. Each JSON object representing a MIME part will have:
    - a `best_guess` attribute with either `message body` or `attachment` as its value (best guess is based on the headers, namely Content-Type and Content-Disposition).
    - a `headers` object (just as described above) with its headers.
    - a `content` attribute that will contain plain text (if it's the message body), base64-encoded binary data (if it's an attachment AND `publish_attachments` configuration property is set to `true`) otherwise simply the string `<not configured to publish attachment data>` (if it's an attachment AND `publish_attachments` configuration property is set to `false`).
    - a `saved_file_name` attribute that will contain the full path and file name of the saved attachment, ONLY if it's an attachment AND `save_attachments` configuration property is set to `true` (the file name will be prefixed with the aforementioned `uuid`).

By default, the add-on is not configured to publish attachment data nor save it to the file system. Since data can be arbitrary and large this would either stress memory, the file system, or both and since a lot of folks run Home Assistant on a Raspberry Pi with an SD card this extra stress may not be desired. Simply the contents of the message body may be enough for most folks.

For those who need the attachment data then it can be turned on in the configuration settings, as described below.

There is nothing fancy about this add-on, it does just one job - publish email messages to MQTT. The 'fancy' stuff is left to [possibly complex] value templating in Home Assistant itself.

As such, here are two, concrete examples of how to create an MQTT sensor with a value template for parsing the contents of an email:

```
  - name: smtp2mqtt_test1
    state_topic: "smtp2mqtt/sender1@email.address"
    value_template: "{{value_json.headers.subject}}"
    
  - name: smtp2mqtt_test2
    state_topic: "smtp2mqtt/sender2@email.address"
    value_template: >-
        {% set search_pattern = '.*CLIENT\s+INFO.*' %}
        {% set current_state = states('sensor.smtp2mqtt_test2') %}
        {% set value_pattern = '.*\\[client:(.+):.+\\] (is connected to) .+ with (.+) on .*|.*\\[client:(.+):.+\\] (is disconnected from) (.+) on.*' %}
        {{ (value_json.mime_parts[0].content | regex_findall_index(find=value_pattern) | join(' ')) if value_json.mime_parts[0].content is search(search_pattern) else current_state }}
```

The first is just a simple test that sets the state of the sensor to the subject of the email.

The second sets the state to a particular string extracted from the message body but only if the message body *looks* like what we are after, otherwise it sets it back to its previous state. (HINT - this one I use to send notifications when a device connects to my network).

These are just a few examples, I am sure the sky is the limit here...

## Configuration

Add-on configuration:

```yaml

mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_user: 
mqtt_pass: 
mqtt_topic: smtp2mqtt

smtp_auth_required: false

smtp_relay_host: 
smtp_relay_port: 25
smtp_relay_user: 
smtp_relay_pass: 
smtp_relay_starttls: 
smtp_relay_timeout_secs: 10

publish_attachments: false
save_attachments: false

debug: false
```

### Option: `mqtt_host` (optional)

The host name or IP address of the MQTT broker to publish to.

Default value: `core-mosquitto` (this should be the alias of the Mosquitto add-on)

#### Option: `mqtt_port` (optional)

The port of the MQTT broker.

Default value: `1883`

#### Option: `mqtt_user` (optional)

The username for authentication to the MQTT broker.

### Option: `mqtt_pass` (optional)

The password for authentication to the MQTT broker.

### Option: `mqtt_topic` (optional)

The base topic to publish to. Messages will be published to this followed by / followed by the sender address.
Example:

    smtp2mqtt/sender@email.address

Default value: `smtp2mqtt`

### Option: `smtp_auth_required` (optional)

Whether or not to require username/password authentication for incoming SMTP connections.

*It may be necessary to enable this to accommodate some devices (i.e., some, not all, Reolink cameras) that seem to require specifying a username & password in their SMTP configuration.

If enabled, a simple dummy authentication is performed that always returns success, meaning it will accept anything for the username & password.

*Note - TLS will be disabled if this is true and will cause a warning in the log, this is OK.

Default value: `false`

### Option: `smtp_relay_host` (optional)

The host name or IP address of an SMTP server to relay the message through, in order to send it on its way.

If the intent is to 'trap' email then don't define this and this add-on will be an end-state, otherwise defining this will send the email on as before.

#### Option: `smtp_relay_port` (optional)

The port of the SMTP relay server.

Default value: `25`

#### Option: `smtp_relay_user` (optional)

The username for authentication to the SMTP relay server.

### Option: `smtp_relay_pass` (optional)

The password for authentication to the SMTP relay server.

### Option: `smtp_relay_starttls` (optional)

Whether or not to issue the `STARTTLS` SMTP command when connecting to the SMTP relay server.

Default value: `false`

### Option: `smtp_relay_timeout_secs` (optional)

A timeout value (in seconds) for relaying the message.

Default value: `10`

### Option: `publish_attachments` (optional)

Whether or not to publish the attachment data. The MIME part describing the attachment, including its headers, will always be published but unless this is set to `true` the `content` attribute will just contain the string `<not configured to publish attachment data>`.

If set to `true` then the `content` attribute will contain the attachment data, base64 encoded (regardless of how it was originally encoded in the email it will be normalized to base64).

Default value: `false`

### Option: `save_attachments` (optional)

Whether or not to save attachments to the file system.

If set to `true` then attachment data will be written to a sub-directory of the /share folder, named for the `mqtt_topic`. Example:

    /share/smtp2mqtt/

File names will be taken from the Content-Disposition header in the email and will be pre-pended with a UUID (for uniqueness), the full path and file name will be added to the MQTT payload under the `saved_file_name` attribute.

Default Value: `false`

### Option: `debug` (optional)

If set to `true` then additional, debug-level logging will be added to the existing info-level logging. This is useful to see what the published payload looks like and is invaluable when trying to come up with a suitable value template (in the Home Assistent sensor config, etc.) to parse the content of the email.

Beware - turning this on will leak sensitive info to the log file!

Default Value: `false`

## Support

This add-on is as simple & basic as possible, it does one job and leaves the fine details to value templating.

This is on purpose as I don't have a lot of time to address issues.

If there is something egregious then feel free to post on the smtp2mqtt community [forum] or open an [issue] on my GitHub and I'll try to get to it.

[forum]: https://community.home-assistant.io/t/smtp-to-mqtt-add-on
[issue]: https://github.com/bcastellucci/addons/issues
[wicol/emqtt]: https://github.com/wicol/emqtt
