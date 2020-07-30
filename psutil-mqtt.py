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

'''
fh = TimedRotatingFileHandler('/var/log/garagedoor/garagedoor1.log',
    interval=1, when="w6", backupCount=5)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
'''

class PSUtilMetric(object):
    def __init__(self, *args, **kwargs):
        self.icon = "mdi:desktop-tower-monitor"
        self.unit_of_measurement = "%"
        self.topics = None

    def get_config_topic(self, topic_prefix, system_name):
        def sanitize(val):
            return val.lower().replace(" ", "_")
        sn = sanitize(system_name)
        n = sanitize(self.name)
        t = {}
        t['state'] = "{}/sensor/{}/{}/state".format(topic_prefix, sn, n)
        t['config'] = "{}/sensor/{}/{}/config".format(topic_prefix, sn, n)
        t['avail'] = "{}/sensor/{}/{}/availability".format(topic_prefix, sn, n)
        t['attrs'] = "{}/sensor/{}/{}/attributes".format(topic_prefix, sn, n)
        self.topics = t
        
        config_topic = {'name': system_name + ' ' + self.name,
            'unique_id': sn + '_' + n,
            'qos': 1,
            'icon': self.icon,
            'unit_of_measurement': self.unit_of_measurement,
            'availability_topic': t['avail'],
            'json_attributes_topic': t['attrs'],
            'state_topic': t['state']}
        return config_topic

class CPUMetric(PSUtilMetric):
    def __init__(self, interval):
        super(CPUMetric, self).__init__()
        self.name = "CPU"
        self.icon = "mdi:chip"
        self.interval = interval

    def get_state(self):
        r = {}
        cpu_times = psutil.cpu_times_percent(interval=self.interval, percpu=False)
        r['state'] = "{:.1f}".format(100.0 - cpu_times.idle)
        r['attrs'] = jsons.dump(cpu_times)
        return r

class VirtualMemoryMetric(PSUtilMetric):
    def __init__(self, *args, **kwargs):
        super(VirtualMemoryMetric, self).__init__(*args, **kwargs)
        self.name = "Virtual Memory"
        self.icon = "mdi:memory"

    def get_state(self):
        r = {}
        vm = psutil.virtual_memory()
        r['state'] = "{:.1f}".format(vm.percent)
        r['attrs'] = jsons.dump(vm)
        return r

class PSUtilDaemon(object):
    def __init__(self, system_name, broker_host, topic_prefix):
        self.system_name = system_name
        self.broker_host = broker_host
        self.topic_prefix = topic_prefix
        self.metrics = []
        
        signal.signal(signal.SIGTERM, self.sig_handle)
        signal.signal(signal.SIGINT, self.sig_handle)

    def connect(self):
        self.client = mqtt.Client(self.system_name + '_psutilmqtt')
        try: 
              self.client.connect(self.broker_host)
              logger.info("Connected to MQTT broker.")
              self.client.loop_start()
        except Exception as e:
              logger.error("Error while trying to connect to MQTT broker.")
              logger.error(str(e))
              raise

    def _report_status(self, avail_topic, status):
        if status: status = 'online'
        else: status = 'offline'
        logger.info(self._pub_log(avail_topic, status))
        self.client.publish(avail_topic, status, retain=True, qos=1)

    def sig_handle(self, signum, frame):
        self._cleanup(0)

    def _cleanup(self, exit_code=0):
        logger.warning("Shutting down gracefully.")
        for metric in self.metrics:
            self._report_status(metric.topics['avail'], False)
        self.client.loop_stop() 
        self.client.disconnect()
        sys.exit(exit_code)

    def _pub_log(self, topic, msg):
        return "Publishing '{}' to topic '{}'.".format(msg, topic)

    def create_config_topics(self):
        for metric in self.metrics:
            config_topic = metric.get_config_topic(self.topic_prefix, self.system_name)
            logger.debug(self._pub_log(metric.topics['config'], config_topic))
            self.client.publish(metric.topics['config'], json.dumps(config_topic), retain=True, qos=1)
            self._report_status(metric.topics['avail'], True)

    def clean(self):
        raise NotImplementedError("Clean function doesn't work yet.")

    def add_metric(self, metric):
        self.metrics.append(metric)

    def monitor(self):
        self.create_config_topics()
        while True:
            for metric in self.metrics:
                s = metric.get_state()
                state = s['state']
                attrs = json.dumps(s['attrs'])
                logger.debug(self._pub_log(metric.topics['state'], state))
                self.client.publish(metric.topics['state'], state, retain=False, qos=1)
                logger.debug(self._pub_log(metric.topics['attrs'], attrs))
                self.client.publish(metric.topics['attrs'], attrs, retain=False, qos=1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", help="Clean up retained MQTT messages and stuff and exit", action="store_true")
    parser.add_argument("--config", help="Create MQTT config topic and exit", action="store_true")

    parser.add_argument('--name', required=True,
                    help='A descriptive name for the computer being monitored.')
    parser.add_argument('--broker', default="localhost",
                    help='Hostname or IP address of the MQTT broker (default: localhost)')
    parser.add_argument('--prefix', default="homeassistant",
                    help='MQTT topic prefix (default: homeassistant)')
    parser.add_argument("-v", "--verbosity", action="count", default=1,
                    help='Log verbosity (default: 1 (critical errors))')

    parser.add_argument("--cpu", help="Publish CPU metrics", type=int, 
                        nargs="?", const=60, default=None, metavar='INTERVAL')
    parser.add_argument("--vm", help="Publish virtual memory", action="store_true")
    args = parser.parse_args()
    system_name = args.name
    broker_host = args.broker
    topic_prefix = args.prefix

    ch = logging.StreamHandler()
    if args.verbosity >= 5:
        ch.setLevel(logging.DEBUG)
    elif args.verbosity == 4:
        ch.setLevel(logging.INFO)
    elif args.verbosity == 3:
        ch.setLevel(logging.WARNING) 
    elif args.verbosity == 2:
        ch.setLevel(logging.ERROR)
    elif args.verbosity == 1:
        ch.setLevel(logging.CRITICAL)
    if args.verbosity > 0:
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    stats = PSUtilDaemon(system_name, broker_host, topic_prefix)
    if args.cpu:
        cpu = CPUMetric(interval=args.cpu)
        stats.add_metric(cpu)
    if args.vm:
        vm = VirtualMemoryMetric()
        stats.add_metric(vm)
    if not args.vm or args.cpu:
        logger.warning("No metrics specified. Nothing will be published.")
    stats.connect()

    if args.clean:
        stats.clean()
    elif args.config:
        stats.create_config_topic(exit=True)
    else:
        stats.monitor()