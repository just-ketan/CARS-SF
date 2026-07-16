# RSNSD Feature Catalog

| Feature | Category | Type | Source | ML Role | Description |
|---------|----------|------|--------|---------|-------------|
| flow_id | flow | string | flow_extractor | metadata | Unique identifier of the network flow |
| flow_duration_ms | flow | float | flow_extractor | feature | Total duration of the network flow |
| packet_count | flow | int | flow_extractor | feature | Total number of packets in the flow |
| byte_count | flow | int | flow_extractor | feature | Total bytes transferred |
| forward_packet_count | flow | int | flow_extractor | feature | Packets sent from source to destination |
| backward_packet_count | flow | int | flow_extractor | feature | Packets sent from destination to source |
| forward_byte_count | flow | int | flow_extractor | feature | Bytes transferred from source to destination |
| backward_byte_count | flow | int | flow_extractor | feature | Bytes transferred from destination to source |
| packet_rate_pps | flow | float | flow_extractor | feature | Packets transmitted per second |
| byte_rate_bps | flow | float | flow_extractor | feature | Bytes transmitted per second |
| flow_start_time | flow | datetime | flow_extractor | metadata | Timestamp when the flow started |
| flow_end_time | flow | datetime | flow_extractor | metadata | Timestamp when the flow ended |
| ether_type | layer2 | category | packet_parser | feature | Ethernet frame type |
| vlan_present | layer2 | bool | packet_parser | feature | Whether the Ethernet frame contains a VLAN tag |
| vlan_priority | layer2 | int | packet_parser | feature | IEEE 802.1p VLAN priority value |
| broadcast_frame | layer2 | bool | packet_parser | feature | Whether the frame is broadcast |
| multicast_frame | layer2 | bool | packet_parser | feature | Whether the frame is multicast |
| ip_version | layer3 | category | packet_parser | feature | Internet Protocol version |
| ttl | layer3 | int | packet_parser | feature | IPv4 Time-To-Live or IPv6 Hop Limit |
| dscp | layer3 | int | packet_parser | feature | Differentiated Services Code Point |
| ecn | layer3 | int | packet_parser | feature | Explicit Congestion Notification value |
| ip_packet_length | layer3 | int | packet_parser | feature | Total IP packet length |
| fragmented | layer3 | bool | packet_parser | feature | Whether the packet is fragmented |
| ip_header_length | layer3 | int | packet_parser | feature | Length of the IP header |
| hop_limit | layer3 | int | packet_parser | feature | IPv6 Hop Limit (mirrors TTL for IPv6) |
| transport_protocol | layer4 | string | packet_parser | feature | Transport layer protocol used by the flow |
| source_port | layer4 | int | packet_parser | feature | Source transport layer port |
| destination_port | layer4 | int | packet_parser | feature | Destination transport layer port |
| tcp_syn_count | layer4 | int | packet_parser | feature | Number of TCP SYN packets |
| tcp_ack_count | layer4 | int | packet_parser | feature | Number of TCP ACK packets |
| tcp_fin_count | layer4 | int | packet_parser | feature | Number of TCP FIN packets |
| tcp_rst_count | layer4 | int | packet_parser | feature | Number of TCP RST packets |
| tcp_window_size | layer4 | int | packet_parser | feature | Average TCP receive window size |
| tcp_retransmissions | layer4 | int | packet_parser | feature | Number of retransmitted TCP packets |
| udp_packet_count | layer4 | int | packet_parser | feature | Number of UDP packets |
| mean_iat_ms | temporal | float | flow_extractor | feature | Mean inter-arrival time between packets |
| std_iat_ms | temporal | float | flow_extractor | feature | Standard deviation of packet inter-arrival time |
| min_iat_ms | temporal | float | flow_extractor | feature | Minimum packet inter-arrival time |
| max_iat_ms | temporal | float | flow_extractor | feature | Maximum packet inter-arrival time |
| forward_mean_iat_ms | temporal | float | flow_extractor | feature | Mean forward-direction inter-arrival time |
| backward_mean_iat_ms | temporal | float | flow_extractor | feature | Mean backward-direction inter-arrival time |
| flow_active_time_ms | temporal | float | flow_extractor | feature | Total active transmission time |
| flow_idle_time_ms | temporal | float | flow_extractor | feature | Total idle time during the flow |
| mean_packet_size | statistical | float | flow_extractor | feature | Average packet size within the flow |
| median_packet_size | statistical | float | flow_extractor | feature | Median packet size within the flow |
| min_packet_size | statistical | int | flow_extractor | feature | Minimum packet size observed in the flow |
| max_packet_size | statistical | int | flow_extractor | feature | Maximum packet size observed in the flow |
| std_packet_size | statistical | float | flow_extractor | feature | Standard deviation of packet sizes |
| variance_packet_size | statistical | float | flow_extractor | feature | Variance of packet sizes |
| packet_size_range | statistical | int | flow_extractor | feature | Difference between maximum and minimum packet sizes |
| packet_size_skewness | statistical | float | flow_extractor | feature | Skewness of packet size distribution |
| packet_size_kurtosis | statistical | float | flow_extractor | feature | Kurtosis of packet size distribution |
| coefficient_of_variation_packet_size | statistical | float | flow_extractor | feature | Coefficient of variation of packet sizes |
| end_to_end_latency_ms | qos | float | qos_estimator | feature | Average end-to-end latency experienced by the flow |
| jitter_ms | qos | float | qos_estimator | feature | Variation in packet arrival time |
| packet_loss_rate | qos | float | qos_estimator | feature | Percentage of packets lost during transmission |
| throughput_mbps | qos | float | qos_estimator | feature | Average throughput achieved by the flow |
| goodput_mbps | qos | float | qos_estimator | feature | Application-level useful throughput excluding retransmissions |
| bandwidth_utilization_pct | qos | float | qos_estimator | feature | Percentage of allocated bandwidth utilized |
| queueing_delay_ms | qos | float | qos_estimator | feature | Average queueing delay experienced by packets |
| retransmission_rate | qos | float | qos_estimator | feature | Percentage of retransmitted packets |
| link_utilization_pct | qos | float | qos_estimator | feature | Percentage utilization of the serving link |
| qos_satisfaction_score | qos | float | qos_estimator | feature | Composite QoS score derived from latency, jitter, packet loss and throughput |
| service_type | context | category | context_injector | feature | High-level service category |
| application_name | context | string | context_injector | feature | Application generating the traffic |
| slice_type | context | category | context_injector | feature | Target network slice type |
| service_priority | context | int | context_injector | feature | Priority assigned to the service |
| network_load_pct | context | float | context_injector | feature | Overall network utilization |
| cell_load_pct | context | float | context_injector | feature | Serving cell utilization |
| active_users | context | int | context_injector | feature | Number of active users in the serving cell |
| device_type | context | category | context_injector | feature | Type of user equipment |
| mobility_state | context | category | context_injector | feature | Mobility state of the user |
| time_of_day | context | category | context_injector | feature | Time period when the flow was generated |
| signal_strength_dbm | context | float | context_injector | feature | Average received signal strength |
| sinr_db | context | float | context_injector | feature | Signal-to-Interference-plus-Noise Ratio |
| rsrp_dbm | context | float | context_injector | feature | Reference Signal Received Power |
| rsrq_db | context | float | context_injector | feature | Reference Signal Received Quality |
| cqi | context | int | context_injector | feature | Channel Quality Indicator |
| network_slice_id | context | category | context_injector | feature | Identifier of the serving network slice |
| slice_resource_utilization_pct | context | float | context_injector | feature | Percentage of slice resources currently utilized |
| radio_resource_blocks_used | context | int | context_injector | feature | Allocated Physical Resource Blocks |
| handover_in_progress | context | bool | context_injector | feature | Whether the UE is undergoing handover |
| service_class | label | category | labeler | label | Ground truth service class |
| application_id | label | category | labeler | label | Application responsible for generating the flow |
| slice_type_label | label | category | labeler | label | Ground truth slice type |
| priority_level | label | int | labeler | label | Ground truth service priority |
| allocated_slice | label | category | labeler | label | Slice allocated by the scheduling policy |
| sla_satisfied | label | bool | labeler | label | Whether the flow met its SLA requirements |
| reward_score | label | float | labeler | label | Reward assigned to the scheduling decision |