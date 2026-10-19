class ContextEngine:
	CONTEXTS = {
		"normal":{
			"healthcare": 5,
			"education": 4,
			"agriculture": 3,
			"general": 1,
		},

		"school":{
			"healthcare": 5,
			"education": 5,
			"agriculture": 2,
			"general" : 1
		},

		"harvest":{
			"healthcare": 5,
			"education" : 3,
			"agriculture": 5,
			"general": 1
		},

		"disaster": {
			"healthcare": 10,
			"education" : 1,
			"agriculture" : 1,
			"general" : 1
		},

		"medical_emergency": {
			"healthcare": 15,
			"education": 1,
			"agriculture": 1,
			"general": 1,
		},

		"fiber_cut": {
			"healthcare": 10,
			"education": 2,
			"agriculture": 2,
			"general": 1,
		},
	}

	def __init__(self):
		# Scenario registry is the source of truth; CONTEXTS is the fallback.
		self.contexts = {**self.CONTEXTS, **_registry_priorities()}

	def get_context(self, context):
		if context not in self.contexts:
			raise ValueError(f"unknown context: {context}")
		return dict(self.contexts[context])


def _registry_priorities():
	try:
		from core.config import load_scenarios
		return {s["id"]: s["priority_weights"] for s in load_scenarios() if "priority_weights" in s}
	except Exception:
		return {}

if __name__ == "__main__":
	ce = ContextEngine()
	print(ce.get_context("school"))
