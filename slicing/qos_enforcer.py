class QoSEnforcer:

    INTERFACE = "s1-eth1"

    def apply_allocation(
        self,
        allocation
    ):

        print("\nGenerated OVS Commands")
        print("----------------------")

        for service, bandwidth in allocation.items():

            command = (
                f"ovs-vsctl "
                f"# {service} "
                f"rate={bandwidth}Mbps"
            )

            print(command)