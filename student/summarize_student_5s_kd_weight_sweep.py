#!/usr/bin/env python3
from pathlib import Path
import json
import pandas as pd

repo = Path(__file__).resolve().parents[1]
results = repo / "student" / "results"

birds = ["23birdchirping", "24wingflapping"]
confusers = ["02rain", "07treefalling", "21insect", "27squirrel"]

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def add_folder_metrics(row, run_dir):
    p = run_dir / "per_folder_metrics.csv"
    if not p.exists():
        return row
    df = pd.read_csv(p)
    for folder in birds:
        r = df[df["source_folder"] == folder]
        if len(r):
            row[f"{folder}_recall"] = float(r.iloc[0]["recall_if_bird"])
    for folder in confusers:
        r = df[df["source_folder"] == folder]
        if len(r):
            row[f"{folder}_fp_rate"] = float(r.iloc[0]["fp_rate_if_nonbird"])
    return row

def summarize(run_dir, label):
    p = run_dir / "metrics_summary.json"
    if not p.exists():
        return None
    s = load_json(p)
    row = {
        "label": label,
        "run_name": run_dir.name,
        "hard_weight": s.get("hard_weight", None),
        "kd_weight": s.get("kd_weight", None),
        "precision_0p5": s.get("precision_0p5_mean", None),
        "recall_0p5": s.get("recall_0p5_mean", None),
        "f1_0p5": s.get("f1_0p5_mean", None),
        "pr_auc": s.get("pr_auc_mean", None),
        "roc_auc": s.get("roc_auc_mean", None),
        "recall_at_fpr_target": s.get("recall_at_fpr_target_mean", None),
        "fpr_at_target": s.get("fpr_at_target_mean", None),
    }
    return add_folder_metrics(row, run_dir)

rows = []
for run, label in [
    ("5s_hardlabel_baseline_v2", "hard-label v2"),
    ("5s_kd_binary_v1", "KD v1 0.5/0.5"),
]:
    r = summarize(results / run, label)
    if r:
        rows.append(r)

for d in sorted(results.glob("5s_kd_binary_hw*_kw*")):
    r = summarize(d, d.name)
    if r:
        rows.append(r)

if not rows:
    raise SystemExit("No metrics_summary.json files found.")

df = pd.DataFrame(rows)
df["rank_score"] = df["recall_at_fpr_target"].fillna(-1) * 10 + df["pr_auc"].fillna(-1)
df = df.sort_values("rank_score", ascending=False).drop(columns=["rank_score"])

csv_path = results / "kd_weight_sweep_summary.csv"
md_path = results / "kd_weight_sweep_summary.md"
df.to_csv(csv_path, index=False)

cols = [
    "label", "run_name", "hard_weight", "kd_weight",
    "precision_0p5", "recall_0p5", "f1_0p5",
    "pr_auc", "roc_auc", "recall_at_fpr_target", "fpr_at_target",
    "23birdchirping_recall", "24wingflapping_recall",
    "02rain_fp_rate", "07treefalling_fp_rate", "21insect_fp_rate", "27squirrel_fp_rate",
]
cols = [c for c in cols if c in df.columns]

lines = []
lines.append("# KD Weight Sweep Summary")
lines.append("")
lines.append("Ranking is sorted primarily by `recall_at_fpr_target`, then PR-AUC.")
lines.append("")
lines.append(df[cols].to_markdown(index=False))
lines.append("")
lines.append("## Decision rule")
lines.append("")
lines.append("Prefer the model with the best `recall_at_fpr_target` and PR-AUC without unacceptable false positives on rain, treefalling, insect, and squirrel.")
lines.append("")
lines.append("Generated files:")
lines.append("")
lines.append("- `student/results/kd_weight_sweep_summary.csv`")
lines.append("- `student/results/kd_weight_sweep_summary.md`")
lines.append("")

md_path.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {csv_path}")
print(f"Wrote {md_path}")
print(df[cols].to_string(index=False))

