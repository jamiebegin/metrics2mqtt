# psutil-mqtt
Publish hardware monitoring data from psutil to a MQTT broker

`psutil-mqtt` is a lightweight wrapper around [psutil](https://pypi.org/project/psutil/) that publishes CPU utilization, free memory, and other system-level stats to a MQTT broker. The primary use case is to collect system stats for ingestion into Home Assistant (HA) for alerting, reporting, and firing off any number of automations. However, given the minimal nature of this code, it could be used other purposes as well.

This project is intended to be an alternative to the (very good) [Glances](https://github.com/nicolargo/glances) project. The primary design difference is that the Glances integration into Home Assistant relies on periodically polling a RESTful API. However, the pub/sub model of MQTT is a better fit for real-time reporting of this type of data. Additionally, MQTT is already widely used in the HA community. 