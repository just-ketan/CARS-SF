## Given limited bandwidth, how to decide who gets how much ?

class PriorityEngine:
	def __init__(self):
		self.weights = {}

	def set_weights(self, weights):
		self.weights = weights

	def allocate_bandwidth(self, total_bandwidth):
		tot_weight = sum(self.weights.values())
		allocation = {}
		for srvc, wt in self.weights.items():
			allocation[srvc] = round(total_bandwidth*wt / tot_weight, 2)
		return allocation
