import json, jsons
import psutil

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

    def get_state(self):
        raise NotImplementedError

class CPUMetrics(PSUtilMetric):
    def __init__(self, interval):
        super(CPUMetrics, self).__init__()
        self.name = "CPU"
        self.icon = "mdi:chip"
        self.interval = interval

    def get_state(self):
        r = {}
        cpu_times = psutil.cpu_times_percent(interval=self.interval, percpu=False)
        r['state'] = "{:.1f}".format(100.0 - cpu_times.idle)
        r['attrs'] = jsons.dump(cpu_times)
        return r

class VirtualMemoryMetrics(PSUtilMetric):
    def __init__(self, *args, **kwargs):
        super(VirtualMemoryMetrics, self).__init__(*args, **kwargs)
        self.name = "Virtual Memory"
        self.icon = "mdi:memory"

    def get_state(self):
        r = {}
        vm = psutil.virtual_memory()
        r['state'] = "{:.1f}".format(vm.percent)
        r['attrs'] = jsons.dump(vm)
        return r

class DiskUsageMetrics(PSUtilMetric):
    def __init__(self, mountpoint):
        super(DiskUsageMetrics, self).__init__()
        self.name = "Disk Usage"
        self.icon = "mdi:harddisk"
        self.mountpoint = mountpoint

    def get_state(self):
        r = {}
        disk = psutil.disk_usage(self.mountpoint)
        r['state'] = "{:.1f}".format(disk.percent)
        r['attrs'] = jsons.dump(disk)
        return r

    def get_config_topic(self, topic_prefix, system_name):
        def sanitize(val):
            return val.lower().replace(" ", "_").replace("/","_")
        sn = sanitize(system_name)
        n = sanitize(self.mountpoint)
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
