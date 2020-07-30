#!/usr/bin/env python3
import sys
import signal
import argparse
import logging
import json, jsons
import paho.mqtt.client as mqtt
import psutil

logger = logging.getLogger('psutil-mqtt')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)
'''
fh = TimedRotatingFileHandler('/var/log/garagedoor/garagedoor1.log',
    interval=1, when="w6", backupCount=5)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
'''
class PSUtilDaemon(object):
    def __init__(self, system_name, broker_host, topics):
        self.system_name = system_name
        self.broker_host = broker_host
        self.topics = topics
        
        signal.signal(signal.SIGTERM, self.sig_handle)
        signal.signal(signal.SIGINT, self.sig_handle)

    def connect(self):
        self.client = mqtt.Client(self.system_name + '_psutilmqtt')
        try: 
              self.client.connect(self.broker_host)
              logger.info("Connected to MQTT broker.")
              self._report_status(True)
              self.client.loop_start()
        except Exception as e:
              logger.error("Error while trying to connect to MQTT broker.")
              logger.error(str(e))
              raise

    def _report_status(self, status):
        if status: status = 'online'
        else: status = 'offline'
        logger.debug('Publishing "{}" to {}'.format(status, self.topics['avail']))
        self.client.publish(self.topics['avail'], status, retain=True, qos=1)

    def sig_handle(self, signum, frame):
        self._cleanup(0)

    def _cleanup(self, exit_code=0):
        logger.warning("Shutting down gracefully.")
        self._report_status(False)
        self.client.loop_stop() 
        self.client.disconnect()
        sys.exit(exit_code)

    def config(self, exit=False):
        p = {'name': self.system_name + ' CPU',
        'unique_id': self.system_name + '_cpu',
        'qos': 1,
        'icon': 'mdi:chip',
        'unit_of_measurement': '%',
        'availability_topic': self.topics['avail'],
        'json_attributes_topic': self.topics['attrs'],
        'state_topic': self.topics['state']}
        self.client.publish(self.topics['config'], json.dumps(p), retain=True, qos=1)
        if exit:
            logger.critical("Exiting after creating new topic: {}".format(p))  
            self._cleanup()

    def clean(self):
        raise NotImplementedError("Clean function doesn't work yet.")

    def cpu(self):
        cpu_times = psutil.cpu_times_percent(interval=60, percpu=False)
        new_state = "{:.1f}".format(100.0 - cpu_times.idle)
        attrs = jsons.dump(cpu_times)
        logger.debug("Publishing '{}' to {}".format(json.dumps(new_state), self.topics['state']))
        self.client.publish(self.topics['state'], new_state, retain=False, qos=1)
        logger.debug("Publishing '{}' to {}".format(json.dumps(attrs), self.topics['attrs']))
        self.client.publish(self.topics['attrs'], json.dumps(attrs), retain=False, qos=1)

    def monitor(self):
        self.config()
            while True:
                self.cpu()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", help="Clean up retained MQTT messages and stuff and exit", action="store_true")
    parser.add_argument("--config", help="Create MQTT config topic and exit", action="store_true")
   
    args = parser.parse_args()

    system_name = 'nuc'
    metric = 'cpu'
    broker_host = "192.168.7.60"
    topic_prefix = "homeassistant"
    topics = {}
    topics['state'] = "{}/sensor/{}/{}/state".format(topic_prefix, system_name, metric)
    topics['config'] = "{}/sensor/{}/{}/config".format(topic_prefix, system_name, metric)
    topics['avail'] = "{}/sensor/{}/{}/availability".format(topic_prefix, system_name, metric)
    topics['attrs'] = "{}/sensor/{}/{}/attributes".format(topic_prefix, system_name, metric)

    stats = PSUtilDaemon(system_name, broker_host, topics)
    stats.connect()

    if args.clean:
        stats.clean()
    elif args.config:
        stats.config(exit=True)
    else:
        stats.monitor()