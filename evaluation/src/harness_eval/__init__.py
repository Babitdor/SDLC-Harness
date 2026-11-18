"""SDLC Harness Evaluation Framework.

Evaluates the multi-agent pipeline across four dimensions:
  1. Artifact quality — the harness's own artifact gates
  2. Agent trajectory — subagent call order matches DAG
  3. Pipeline completeness — all expected artifacts produced
  4. End-to-end correctness — LLM-as-judge scoring

Usage:
    python -m harness_eval run --dataset pipeline-completeness
    python -m harness_eval list-datasets
"""

from __future__ import annotations