# SOVARA Benchmark & Evaluation Suite

This directory contains the industrial benchmarking infrastructure for the SOVARA AI Core.
It evaluates the system on determinism, multi-modal reasoning, hallucination resistance, and tool execution.

## File Structure
- questions.json: The benchmark dataset containing input queries, files, and ground truth expectations.
- evaluation_config.json: Configuration for the benchmark runner (tolerances, timeouts).
- enchmark_runner.py: The execution harness that pipes tasks into the existing SOVARA backend.
- scoring.py: Deterministic scoring algorithms computing retrieval accuracy, hallucination rates, etc.

## External Datasets
Future external datasets should be placed in datasets/external/ without modifying the core system.
The benchmark runner can easily be extended to iterate over:
- datasets/external/pump_vibration/
- datasets/external/pidqa/
- datasets/external/tennessee_eastman/

To use external datasets, simply generate a new questions.json referencing paths within the external directory.

## How to Run
`ash
python datasets/benchmark/benchmark_runner.py
`
Outputs will be logged to datasets/benchmark/benchmark_results.json.
