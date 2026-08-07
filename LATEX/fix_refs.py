import re
import os

filepath = "/home/ketan/Desktop/Projects/CARS-SF/LATEX/IT_report.tex"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix broken references by removing sentences referencing undefined figures
broken_figs = [
    "fig:private5g", "fig:system_overview", "fig:mininet_topology", 
    "fig:feature_pipeline", "fig:dataset_pipeline", "fig:dataset_motivation",
    "fig:rsnsd_pipeline", "fig:synthetic_pipeline", "fig:label_generation",
    "fig:validation", "fig:source_distribution", "fig:classification_problem",
    "fig:feature_preprocessing", "fig:slicenet_architecture", "fig:future_pipeline",
    "fig:experimental_environment", "fig:simulation_architecture", "fig:ml_pipeline",
    "fig:self_healing", "fig:research_motivation", "fig:engineering_roadmap"
]

for fig in broken_figs:
    # Regex to match sentences containing Figure~\ref{fig:xxx}
    # It looks for optional whitespace, "Figure~\ref{fig:xxx}", and removes up to the period.
    # Note: this is a simple heuristic and might need to be adjusted.
    pattern = r'[^.]*?Figure~\\ref\{' + re.escape(fig) + r'\}[^.]*\.'
    content = re.sub(pattern, '', content)
    
    # Also remove if it's "Figures~\ref{fig:xxx}..."
    pattern2 = r'[^.]*?Figures~\\ref\{' + re.escape(fig) + r'\}[^.]*\.'
    content = re.sub(pattern2, '', content)

# Fix chap:future_work
content = content.replace(r'Chapter~\ref{chap:future_work}', r'Chapter~\ref{chap:conclusion}')

# 2. Add Citations
# Intro - 5G and Rural
content = content.replace("Fifth Generation (5G) networks represent a paradigm shift", 
                          r"Fifth Generation (5G) networks represent a paradigm shift~\cite{andrews2014what, boccardi2014five}")

content = content.replace("rural communities often suffer from limited bandwidth", 
                          r"rural communities often suffer from limited bandwidth~\cite{yaseen2018mobile, al2020providing}")

# Background - 5G Architecture
content = content.replace("Fifth Generation (5G) represents a fundamental architectural evolution", 
                          r"Fifth Generation (5G) represents a fundamental architectural evolution~\cite{shafi20175g, chataut2020massive}")

content = content.replace("By incorporating technologies such as Software Defined Networking (SDN)",
                          r"By incorporating technologies such as Software Defined Networking (SDN)~\cite{kreutz2015software, mckeown2008openflow}")

# Background - Network Slicing
content = content.replace("network slicing allows a single physical infrastructure to be partitioned", 
                          r"network slicing allows a single physical infrastructure to be partitioned~\cite{rost2017network, zhang2017network, foukas2017network}")

content = content.replace("Network slicing is widely regarded as one of the most transformative features",
                          r"Network slicing is widely regarded as one of the most transformative features~\cite{barakabitze20205g, kaloxylos2018survey}")

# Background - Machine Learning
content = content.replace("Artificial Intelligence (AI) and Machine Learning (ML) have emerged as essential technologies", 
                          r"Artificial Intelligence (AI) and Machine Learning (ML) have emerged as essential technologies~\cite{boutaba2018comprehensive, wang2017machine}")

content = content.replace("Deep learning techniques, in particular, have demonstrated remarkable success", 
                          r"Deep learning techniques, in particular, have demonstrated remarkable success~\cite{kato2017deep, fadlullah2017state, jiang2017machine}")

content = content.replace("A typical machine learning pipeline for traffic classification consists", 
                          r"A typical machine learning pipeline for traffic classification consists~\cite{nguyen2008survey, pacheco2018machine, wang2015end}")

content = content.replace("network flow statistics, packet-level characteristics, and temporal features", 
                          r"network flow statistics, packet-level characteristics, and temporal features~\cite{lotfollahi2020deep, aceto2019mobile}")

# Experimental Environment
content = content.replace("Mininet network emulator", 
                          r"Mininet network emulator~\cite{lantz2010network, kaur2014mininet}")

content = content.replace("Open vSwitch instances emulate the forwarding behaviour", 
                          r"Open vSwitch instances emulate the forwarding behaviour~\cite{mckeown2008openflow}")

content = content.replace("private 5G communication scenarios",
                          r"private 5G communication scenarios~\cite{yaacoub2020key, suomalainen20185g, chih2014toward}")

# Dataset Engineering
content = content.replace("Although numerous public network traffic datasets are available",
                          r"Although numerous public network traffic datasets are available~\cite{shiravi2012toward}")


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed broken references and inserted citations.")
