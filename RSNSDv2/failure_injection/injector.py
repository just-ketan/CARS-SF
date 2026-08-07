class FaultInjector:
    """
    Phase 9: Failure Injection Framework
    Inject realistic network faults into the live simulation.
    """
    def __init__(self, net):
        self.net = net
        self.fault_active = False

    def evaluate_scenario(self, scenario_profile):
        has_link_degrade = any(f["type"] == "link_degrade" for f in scenario_profile.active_faults)
        
        if has_link_degrade and not self.fault_active:
            # Simulate link down or degrade
            self.net.configLinkStatus('s_edge', 's_core', 'down')
            self.fault_active = True
        elif not has_link_degrade and self.fault_active:
            # Recover
            self.net.configLinkStatus('s_edge', 's_core', 'up')
            self.fault_active = False
            
    def cleanup(self):
        if self.fault_active:
            self.net.configLinkStatus('s_edge', 's_core', 'up')
            self.fault_active = False
