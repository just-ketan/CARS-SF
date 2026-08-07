from dataclasses import dataclass
from enum import Enum

class SliceType(Enum):
    URLLC = "URLLC"
    EMBB = "eMBB"
    MMTC = "mMTC"
    BEST_EFFORT = "Best_Effort"

@dataclass
class ApplicationProfile:
    app_id: str
    name: str
    category: str
    slice_type: SliceType
    protocol: str  # "tcp" or "udp"
    target_bw: str # e.g., "10M"
    duration_distribution: tuple # (mean, std)
    # QoS thresholds for labeling
    latency_threshold_ms: float
    loss_threshold_pct: float

# The Application Registry
class ApplicationRegistry:
    def __init__(self):
        self.applications = [
            # Healthcare (URLLC / eMBB)
            ApplicationProfile("APP_HC_001", "ECG Streaming", "Healthcare", SliceType.URLLC, "tcp", "500K", (300, 50), 10.0, 0.001),
            ApplicationProfile("APP_HC_002", "Remote Diagnosis", "Healthcare", SliceType.URLLC, "udp", "5M", (600, 100), 15.0, 0.01),
            ApplicationProfile("APP_HC_003", "Medical Imaging", "Healthcare", SliceType.EMBB, "tcp", "50M", (30, 10), 50.0, 0.1),
            
            # Agriculture (mMTC)
            ApplicationProfile("APP_AG_001", "Soil Sensors", "Agriculture", SliceType.MMTC, "udp", "10K", (10, 2), 1000.0, 5.0),
            ApplicationProfile("APP_AG_002", "Drone Imaging", "Agriculture", SliceType.EMBB, "tcp", "20M", (120, 30), 100.0, 1.0),
            
            # Education (eMBB)
            ApplicationProfile("APP_ED_001", "Live Lecture Video", "Education", SliceType.EMBB, "udp", "8M", (3600, 600), 100.0, 1.0),
            ApplicationProfile("APP_ED_002", "Assignment Download", "Education", SliceType.EMBB, "tcp", "100M", (60, 20), 500.0, 2.0),
            
            # General Internet (Best Effort)
            ApplicationProfile("APP_GN_001", "Web Browsing", "General", SliceType.BEST_EFFORT, "tcp", "2M", (300, 100), 500.0, 5.0),
            ApplicationProfile("APP_GN_002", "CCTV Surveillance", "General", SliceType.BEST_EFFORT, "udp", "4M", (3600, 0), 200.0, 2.0),
        ]

    def get_by_category(self, category: str):
        return [app for app in self.applications if app.category == category]
        
    def get_all(self):
        return self.applications
