from typing import List
from traffic.flow import Flow


class FlowRegistry:

    def __init__(self):
        self._flows: List[Flow] = []

    def add(self, flow: Flow):
        self._flows.append(flow)

    def all(self):
        return self._flows

    def count(self):
        return len(self._flows)

    def clear(self):
        self._flows.clear()