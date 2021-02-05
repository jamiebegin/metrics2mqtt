#!/usr/bin/env python3
import sys
import time
import signal
import socket
import queue
import argparse
import logging
import json, jsons
import paho.mqtt.client as mqtt
import psutil

from metrics2mqtt.metrics import CPUMetrics, VirtualMemoryMetrics, DiskUsageMetrics, NetworkMetrics

logger = logging.getLogger('metrics2mqtt')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class MQTTMetrics(object):
    def __init__(self, system_name, interval, broker_host, broker_port, username, password, topic_prefix):
        self.system_name = system_name
        self.interval = interval
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix
        self.metrics = []
        self.connected = False

        signal.signal(signal.SIGTERM, self.sig_handle)
        signal.signal(signal.SIGINT, self.sig_handle)
        self.deferred_metrics_queue = queue.Queue()

    def connect(self):
        self.client = mqtt.Client(self.system_name + '_metrics2mqtt')
        try: 
            if self.username or self.password:
                self.client.username_pw_set(self.username, self.password)
            self.client.on_connect = self.on_connect
            self.client.connect(self.broker_host, self.broker_port)
            self.client.loop_start()
        except Exception as e:
            logger.error("Error while trying to connect to MQTT broker.")
            logger.error(str(e))
            raise

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker.")
            self.connected = True
            return
        elif rc == 1:
            logger.error("Connection refused – incorrect protocol version")
        elif rc == 2:
            logger.error("Connection refused – invalid client identifier")
        elif rc == 3:
            logger.error("Connection refused – server unavailable")
        elif rc == 4:
            logger.error("Connection refused – bad username or password")
        elif rc == 5:
            logger.error("Connection refused – not authorised")
        else:
            logger.error("Connection refused")
        sys.exit(1)

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

    def add_metric(self, metric):
        self.metrics.append(metric)

    def _check_queue(self):
        while not self.deferred_metrics_queue.empty():
            queued_metric = self.deferred_metrics_queue.get()
            self._publish_metric(queued_metric)

    def _publish_metric(self, metric):
        state = metric.polled_result['state']
        attrs = json.dumps(metric.polled_result['attrs'])
        logger.debug(self._pub_log(metric.topics['state'], state))
        self.client.publish(metric.topics['state'], state, retain=False, qos=1)
        logger.debug(self._pub_log(metric.topics['attrs'], attrs))
        self.client.publish(metric.topics['attrs'], attrs, retain=False, qos=1)

    def monitor(self):
        while not self.connected:
            logger.debug("Waiting for connection.")
            time.sleep(1)

        self.create_config_topics()
        while True:
            x = 0
            while x < self.interval:
                # Check the queue for deferred results one/sec
                time.sleep(1)
                self._check_queue()
                x += 1
            for metric in self.metrics:
                is_deferred = metric.poll(result_queue=self.deferred_metrics_queue)
                if not is_deferred:
                    self._publish_metric(metric)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default=socket.gethostname(),
                    help='A descriptive name for the computer being monitored (default: hostname)')
    parser.add_argument('--broker', default="localhost",
                    help='Hostname or IP address of the MQTT broker (default: localhost)')
    parser.add_argument('--port', default=1883, type=int,
                    help='Port of the MQTT broker (default: 1883)')
    parser.add_argument('--username', default=None,
                    help='Username for MQTT broker authentication (default: None)')
    parser.add_argument('--password', default=None,
                    help='Password for MQTT broker authentication (default: None)')                     
    parser.add_argument('--interval', default=300, type=int,
                    help='Publish metrics to MQTT broker every n seconds (default: 300)')
    parser.add_argument('--prefix', default="homeassistant",
                    help='MQTT topic prefix (default: homeassistant)')
    parser.add_argument("-v", "--verbosity", action="count", default=0,
                    help='Log verbosity (default: 0 (log output disabled)')
    parser.add_argument("--cpu", help="Publish CPU metrics", type=int, 
                        nargs="?", const=60, default=None, metavar='INTERVAL')
    parser.add_argument("--vm", help="Publish virtual memory", action="store_true")
    parser.add_argument("--du", help="Publish disk usage metrics", type=str, action="append", 
                        nargs="?", const='/', default=None, metavar='MOUNT')
    parser.add_argument("--net", help="Publish network interface metrics. Specify the interface name and collection interval seperated by a comma", type=str, action="append", 
                        nargs="?", const='/', default=None, metavar='NIC')

    args = parser.parse_args()
    system_name = args.name
    broker_host = args.broker
    broker_port = args.port
    topic_prefix = args.prefix
    interval = args.interval
    username = args.username
    password = args.password

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

    stats = MQTTMetrics(system_name, interval, broker_host, broker_port, username, password, topic_prefix)
    if args.cpu:
        cpu = CPUMetrics(interval=args.cpu)
        stats.add_metric(cpu)
    if args.vm:
        vm = VirtualMemoryMetrics()
        stats.add_metric(vm)

    if args.du:
        for mountpoint in args.du:
            du = DiskUsageMetrics(mountpoint=mountpoint)
            stats.add_metric(du)

    if args.net:
        for nic in args.net:
            try:
                n, i = nic.split(',')
                i = int(i)
            except ValueError:
                n = nic
                i = 15
            net = NetworkMetrics(n,i)
            stats.add_metric(net)

    if not (args.vm or args.cpu or args.du or args.net):
        logger.warning("No metrics specified. Nothing will be published.")

    stats.connect()
    stats.monitor()

if __name__ == "__main__":
    main()