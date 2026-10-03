
"""
analysis.py - Customer Support Quality Analysis (Set B)

Run (from the repository root, or from anywhere):
    pip install -r requirements.txt
    python python/analysis.py

All paths are relative to the repo root (resolved from this file's location),
so the script runs unmodified on any machine after `git clone`.
"""

import os
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ------------------------------------------------------------------
# P1 - Load, Clean & Merge
# ------------------------------------------------------------------
# Paths are resolved from this file's location, so the script works from the
# repo root OR from inside the python/ folder (no path edits needed).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TICKETS_PATH = os.path.join(REPO_ROOT, "data", "raw", "tickets.csv")
TEAMS_PATH = os.path.join(REPO_ROOT, "data", "raw", "teams.csv")
OUT_DIR = os.path.join(REPO_ROOT, "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

tickets = pd.read_csv(TICKETS_PATH, dtype={"team_id": str, "month": str, "channel": str})
teams = pd.read_csv(TEAMS_PATH, dtype=str)

# Confirm numeric types
tickets["ticket_id"] = tickets["ticket_id"].astype(int)
tickets["resolution_hours"] = pd.to_numeric(tickets["resolution_hours"])
tickets["satisfaction"] = pd.to_numeric(tickets["satisfaction"])
print("Dtypes:\n", tickets.dtypes.to_string(), "\n")

raw_row_count = len(tickets)
tickets_clean = tickets.drop_duplicates(keep="first").reset_index(drop=True)
clean_row_count = len(tickets_clean)
print(f"Raw ticket rows   : {raw_row_count}")
print(f"Clean ticket rows : {clean_row_count} (duplicate removed)")
assert raw_row_count == 13, "Expected 13 raw rows"
assert clean_row_count == 12, "Expected 12 rows after de-duplication"

merged = tickets_clean.merge(teams, on="team_id", how="left")
assert len(merged) == 12, "Merged DataFrame must have exactly 12 rows"
assert merged["department"].isna().sum() == 0, "Unmatched team_id found"
print("Merge check passed: 12 rows, 0 unmatched team_id values.")

# ------------------------------------------------------------------
# P2 - Derived field & department analysis
# ------------------------------------------------------------------
merged["breach_flag"] = (merged["resolution_hours"] > 24).astype(int)

department_summary = (
    merged.groupby("department")
    .agg(total_tickets=("ticket_id", "count"), breached=("breach_flag", "sum"),
         avg_resolution_hours=("resolution_hours", "mean"))
    .reset_index()
)
department_summary["sla_breach_rate_pct"] = (
    department_summary["breached"] / department_summary["total_tickets"] * 100
).round(2)
department_summary["avg_resolution_hours"] = department_summary["avg_resolution_hours"].round(2)
department_summary = department_summary.sort_values(
    "sla_breach_rate_pct", ascending=False
).reset_index(drop=True)

team_summary = (
    merged.groupby("team")
    .agg(total_tickets=("ticket_id", "count"), breached=("breach_flag", "sum"))
    .reset_index()
)
team_summary["breach_rate_pct"] = (
    team_summary["breached"] / team_summary["total_tickets"] * 100
).round(2)
top_teams = team_summary[team_summary["breach_rate_pct"] == team_summary["breach_rate_pct"].max()]

overall_rate = round(merged["breach_flag"].sum() / len(merged) * 100, 2)

print("\nSLA breach summary by department:")
print(department_summary.to_string(index=False))
print(f"\nOverall SLA breach rate: {overall_rate:.2f}% "
      f"({merged['breach_flag'].sum()} of {len(merged)} tickets)")
print("\nTeam(s) with the highest breach rate (all ties reported):")
for _, r in top_teams.iterrows():
    print(f"  {r['team']}: {int(r['breached'])} breached / "
          f"{int(r['total_tickets'])} total = {r['breach_rate_pct']:.2f}%")

# ------------------------------------------------------------------
# P3 - Chart & exports
# ------------------------------------------------------------------
month_order = ["Jan", "Feb", "Mar"]
monthly = merged.groupby("month")["resolution_hours"].mean().reindex(month_order)

fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(monthly.index, monthly.values, color="#C44E52")
ax.axhline(24, color="black", linestyle="--", linewidth=1, label="24h SLA limit")
ax.set_title("Average Resolution Hours by Month (Jan \u2192 Feb \u2192 Mar)")
ax.set_xlabel("Month")
ax.set_ylabel("Average Resolution Hours")
for i, v in enumerate(monthly.values):
    ax.text(i, v, f"{v:.2f}", ha="center", va="bottom")
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "python_chart.png"), dpi=150)
plt.close(fig)

merged.to_csv(os.path.join(OUT_DIR, "clean_data.csv"), index=False)
department_summary.to_csv(os.path.join(OUT_DIR, "python_summary.csv"), index=False)

print("\nSaved chart   -> outputs/python_chart.png")
print("Saved data    -> outputs/clean_data.csv")
print("Saved summary -> outputs/python_summary.csv")