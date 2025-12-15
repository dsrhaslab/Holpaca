#!/bin/bash
python3 experiments/main.py motivation_1 -l 100 -c 800_000_000 -m 60
python3 experiments/main.py motivation_2 -l 100 -c 800_000_000 -m 60
#python3 experiments/main.py use_case_1 -l 100 -c 250_000_000 -t twitter-traces
#python3 experiments/main.py use_case_2 -l 100 -c 250_000_000 -t twitter-traces
#python3 experiments/main.py use_case_3 -l 100 -c 250_000_000 -t twitter-traces
#python3 experiments/main.py agent_overhead -m 60 -c 200_000_000 -l 100
#python3 experiments/main.py orchestrator_algorithm_latency_breakdown -m 60 -c 200_000_000 -l 100 
#python3 experiments/main.py orchestrator_control_interval -m 60 -c 200_000_000 -l 100
