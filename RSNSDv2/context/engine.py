class ContextManager:
    """
    Phase 4: Context Engine
    Maintains active environmental state variables.
    """
    def __init__(self):
        self.weather = "Clear"
        self.power_grid = "Stable"
        self.history = []

    def get_snapshot(self):
        snap = {"weather": self.weather, "power_grid": self.power_grid}
        self.history.append(snap)
        return snap

    def get_history(self):
        return self.history
