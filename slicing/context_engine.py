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
		}
	}

	def get_context(self, context):
		if context not in self.CONTEXTS:
			raise ValueError(f"uknown context: {context}")
		return self.CONTEXTS[context]

if __name__ == "__main__":
	ce = ContextEngine()
	print(ce.get_context("school"))
