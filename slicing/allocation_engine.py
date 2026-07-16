class AllocationEngine:

    def allocate(
        self,
        total_bandwidth,
        priorities,
        demands
    ):

        total_weight = sum(priorities.values())

        allocation = {}
        remaining_bw = total_bandwidth

        # First Pass
        for service in priorities:

            ideal_share = (
                priorities[service]
                / total_weight
            ) * total_bandwidth

            granted = min(
                ideal_share,
                demands[service]
            )

            allocation[service] = granted

            remaining_bw -= granted

        # Second Pass
        while remaining_bw > 0.01:

            unsatisfied = {}

            for service in priorities:

                need = (
                    demands[service]
                    - allocation[service]
                )

                if need > 0:
                    unsatisfied[service] = need

            if not unsatisfied:
                break

            weight_sum = sum(
                priorities[s]
                for s in unsatisfied
            )

            distributed = 0

            for service in unsatisfied:

                share = (
                    priorities[service]
                    / weight_sum
                ) * remaining_bw

                extra = min(
                    share,
                    unsatisfied[service]
                )

                allocation[service] += extra

                distributed += extra

            if distributed < 0.01:
                break

            remaining_bw -= distributed

        return {
            k: round(v, 2)
            for k, v in allocation.items()
        }