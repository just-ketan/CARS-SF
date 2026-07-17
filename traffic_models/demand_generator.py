class DemandGenerator:

    def get_demands(self, context):

        if context == "school":

            return {
                "healthcare": 5,
                "education": 80,
                "agriculture": 10,
                "general": 50
            }

        elif context == "harvest":

            return {
                "healthcare": 5,
                "education": 20,
                "agriculture": 80,
                "general": 50
            }

        elif context == "disaster":

            return {
                "healthcare": 90,
                "education": 5,
                "agriculture": 5,
                "general": 20
            }

        return {
            "healthcare": 20,
            "education": 20,
            "agriculture": 20,
            "general": 20
        }
