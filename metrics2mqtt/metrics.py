import time
import threading, queue
import json, jsons
import psutil
from numpy import array, diff, average

class BaseMetric(object):
    def __init__(self, *args, **kwargs):
        self.icon = "mdi:desktop-tower-monitor"
        self.unit_of_measurement = "%"
        self.topics = None
        self.polled_result = None

    def get_config_topic(self, topic_prefix, system_name):
        sn = self.sanitize(system_name)
        n = self.sanitize(self.name)
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

    def sanitize(self, val):
        return val.lower().replace(" ", "_").replace("/","_")

    def poll(self, result_queue=None):
        raise NotImplementedError

class CPUMetricThread(threading.Thread):
    def __init__(self, result_queue, metric):
        threading.Thread.__init__(self)
        self.result_queue = result_queue
        self.metric = metric

    def run(self):
        r = {}
        cpu_times = psutil.cpu_times_percent(interval=self.metric.interval, percpu=False)
        r['state'] = "{:.1f}".format(100.0 - cpu_times.idle)
        r['attrs'] = jsons.dump(cpu_times)
        self.metric.polled_result = r
        self.result_queue.put(self.metric)

class CPUMetrics(BaseMetric):
    def __init__(self, interval):
        super(CPUMetrics, self).__init__()
        self.name = "CPU"
        self.icon = "mdi:chip"
        self.interval = interval
        self.result_queue = None

    def poll(self, result_queue=None):
        self.result_queue = result_queue
        th = CPUMetricThread(result_queue=result_queue, metric=self)
        th.daemon = True
        th.start()
        return True # Expect a deferred result

class VirtualMemoryMetrics(BaseMetric):
    def __init__(self, *args, **kwargs):
        super(VirtualMemoryMetrics, self).__init__(*args, **kwargs)
        self.name = "Virtual Memory"
        self.icon = "mdi:memory"

    def poll(self, result_queue=None):
        r = {}
        vm = psutil.virtual_memory()
        r['state'] = "{:.1f}".format(vm.percent)
        r['attrs'] = jsons.dump(vm)
        self.polled_result = r
        return False

class DiskUsageMetrics(BaseMetric):
    def __init__(self, mountpoint):
        super(DiskUsageMetrics, self).__init__()
        self.name = "Disk Usage"
        self.icon = "mdi:harddisk"
        self.mountpoint = mountpoint

    def poll(self, result_queue=None):
        r = {}
        disk = psutil.disk_usage(self.mountpoint)
        r['state'] = "{:.1f}".format(disk.percent)
        r['attrs'] = jsons.dump(disk)
        self.polled_result = r
        return False

    def get_config_topic(self, topic_prefix, system_name):
        sn = self.sanitize(system_name)
        n = self.sanitize(self.mountpoint)
        t = {}
        t['state'] = "{}/sensor/{}/disk_usage_{}/state".format(topic_prefix, sn, n)
        t['config'] = "{}/sensor/{}/disk_usage_{}/config".format(topic_prefix, sn, n)
        t['avail'] = "{}/sensor/{}/disk_usage_{}/availability".format(topic_prefix, sn, n)
        t['attrs'] = "{}/sensor/{}/disk_usage_{}/attributes".format(topic_prefix, sn, n)
        self.topics = t
        
        config_topic = {
            'name': system_name + ' Disk Usage (' + self.mountpoint + ' Volume)',
            'unique_id': sn + '_disk_usage_' + n,
            'qos': 1,
            'icon': self.icon,
            'unit_of_measurement': self.unit_of_measurement,
            'availability_topic': t['avail'],
            'json_attributes_topic': t['attrs'],
            'state_topic': t['state']}
        return config_topic

class NetworkMetricThread(threading.Thread):
    def __init__(self, result_queue, metric):
        threading.Thread.__init__(self)
        self.result_queue = result_queue
        self.metric = metric

    def run(self):
        r = {}
        x = 0
        interval = self.metric.interval
        tx_bytes = []
        rx_bytes = []
        prev_tx = 0; prev_rx = 0; base_tx = 0; base_rx = 0
        while x < interval:
            nics = psutil.net_io_counters(pernic=True)
            if self.metric.nic in nics:
                tx = nics[self.metric.nic].bytes_sent
                rx = nics[self.metric.nic].bytes_recv
                if tx < prev_tx:
                    # TX counter rollover
                    base_tx += prev_tx
                if rx < prev_rx:
                    # RX counter rollover
                    base_rx += prev_rx
                tx_bytes.append(base_tx + tx)
                rx_bytes.append(base_rx + rx)
                prev_tx = tx
                prev_rx = rx
            time.sleep(1)
            x += 1
        tx_rate_bytes_sec = average(diff(array(tx_bytes)))
        tx_rate = tx_rate_bytes_sec / 125.0 # bytes/sec to kilobits/sec
        rx_rate_bytes_sec = average(diff(array(rx_bytes)))
        rx_rate = rx_rate_bytes_sec / 125.0 # bytes/sec to kilobits/sec

        r['state'] = "{:.1f}".format(tx_rate + rx_rate)
        r['attrs'] = jsons.dump(nics[self.metric.nic])
        r['attrs'].update({'tx_rate': float("{:.1f}".format(tx_rate)), 'rx_rate': float("{:.1f}".format(rx_rate))})
        self.metric.polled_result = r
        self.result_queue.put(self.metric)

class NetworkMetrics(BaseMetric):
    def __init__(self, nic, interval):
        super(NetworkMetrics, self).__init__()
        self.name = "Network Throughput"
        self.icon = "mdi:server-network"
        self.interval = interval
        self.result_queue = None
        self.unit_of_measurement = "kb/s"
        self.nic = nic        

    def poll(self, result_queue=None):
        self.result_queue = result_queue
        th = NetworkMetricThread(result_queue=result_queue, metric=self)
        th.daemon = True
        th.start()
        return True # Expect a deferred result

    def get_config_topic(self, topic_prefix, system_name):
        sn = self.sanitize(system_name)
        n = self.sanitize(self.nic)
        t = {}
        t['state'] = "{}/sensor/{}/net_{}/state".format(topic_prefix, sn, n)
        t['config'] = "{}/sensor/{}/net_{}/config".format(topic_prefix, sn, n)
        t['avail'] = "{}/sensor/{}/net_{}/availability".format(topic_prefix, sn, n)
        t['attrs'] = "{}/sensor/{}/net_{}/attributes".format(topic_prefix, sn, n)
        self.topics = t
        
        config_topic = {
            'name': system_name + ' Network (' + self.nic + ')',
            'unique_id': sn + '_net_' + n,
            'qos': 1,
            'icon': self.icon,
            'unit_of_measurement': self.unit_of_measurement,
            'availability_topic': t['avail'],
            'json_attributes_topic': t['attrs'],
            'state_topic': t['state']}
        return config_topic