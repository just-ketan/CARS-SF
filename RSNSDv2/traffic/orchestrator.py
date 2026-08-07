import random
from RSNSDv2.registries.application_registry import ApplicationRegistry

class TrafficOrchestrator:
    """
    Phase 2: Traffic Generation Engine
    Emulate deterministic, real-world application behaviors using Linux binaries.
    """
    def __init__(self, net):
        self.net = net
        self.active_processes = []
        self.registry = ApplicationRegistry()
        self._start_servers()

    def _start_servers(self):
        srv_health = self.net.get('mec_hlt')
        srv_cctv = self.net.get('mec_ctv')
        srv_internet = self.net.get('inet')
        
        # Start iperf3 servers on MEC and Core
        srv_health.cmd("iperf3 -s -p 5001 -D")
        srv_cctv.cmd("iperf3 -s -p 5002 -D")
        srv_internet.cmd("iperf3 -s -p 5003 -D")

    def update_demands(self, scenario_state):
        # Stop previous and start new based on demand multipliers
        multiplier = getattr(scenario_state, 'demand_multiplier', 1.0)
        num_apps = max(1, int(3 * multiplier))
        
        apps = random.sample(self.registry.get_all(), min(num_apps, len(self.registry.get_all())))
        for app in apps:
            self.spawn_application(app)
        
    def spawn_application(self, app_profile):
        """Spawn actual iperf3 or ping processes based on profile"""
        hosts = [self.net.get('h_home'), self.net.get('h_school'), self.net.get('h_hospital'), self.net.get('h_farm')]
        host = random.choice(hosts)
        
        # Decide which server to talk to based on app_profile service class or slice
        if "Healthcare" in app_profile.category:
            server_ip = self.net.get('mec_hlt').IP()
            port = 5001
        elif "eMBB" in app_profile.slice_type.value:
            server_ip = self.net.get('mec_ctv').IP()
            port = 5002
        else:
            server_ip = self.net.get('inet').IP()
            port = 5003
            
        bandwidth = app_profile.target_bw
        proto = "-u" if app_profile.protocol == "udp" else ""
        
        # Spawn iperf3 client in background
        cmd = f"iperf3 -c {server_ip} -p {port} -b {bandwidth} {proto} -t 5 > /dev/null 2>&1 &"
        host.cmd(cmd)

    def stop_all(self):
        srv_health = self.net.get('mec_hlt')
        srv_cctv = self.net.get('mec_ctv')
        srv_internet = self.net.get('inet')
        
        srv_health.cmd("pkill iperf3")
        srv_cctv.cmd("pkill iperf3")
        srv_internet.cmd("pkill iperf3")
        
        for p in self.active_processes:
            if p.poll() is None:
                p.terminate()
