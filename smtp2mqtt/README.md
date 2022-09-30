# Home Assistant Add-on: SMTP2MQTT

Turns Home Assistent into an SMTP server, publishes messages (email) to an MQTT broker.

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield] ![Supports armhf Architecture][armhf-shield] ![Supports armv7 Architecture][armv7-shield] ![Supports i386 Architecture][i386-shield]

## About

This add-on is useful for integrating IoT devices that send notifications via email and have no other easily usable way of integrating with Home Assistant.

An example is a camera whose only real option is sending a motion alert email with a picture attached. After installing this add-on the camera could be configured to use Home Assistant as its SMTP server and its email notifications would then be published to an MQTT topic for easy integration into Home Assistant.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg
