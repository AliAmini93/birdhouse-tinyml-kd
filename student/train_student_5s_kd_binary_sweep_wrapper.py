#!/usr/bin/env python3
from pathlib import Path
import argparse, sys

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / "student"))

import train_student_5s_kd_binary_v1 as kd

p = argparse.ArgumentParser()
p.add_argument("--run-name", required=True)
known, rest = p.parse_known_args()

kd.RUN_NAME = known.run_name
sys.argv = ["train_student_5s_kd_binary_v1.py"] + rest
kd.main()

