import pandas as pd
from pathlib import Path

INPUT  = Path("Jupyter/Chaine/data/traces_anonymisees_RGPD_2026_06_09.csv")
OUTPUT = "traces_filtered.csv"

DATE_START = "2024-10-02 15:00:00"
DATE_END   = "2024-10-02 16:00:00"


df = pd.read_csv(INPUT, on_bad_lines="skip", engine="python")
df["ts"] = pd.to_datetime(df["timestamp.$date"], errors="coerce", utc=True)

mask = (df["ts"] >= pd.Timestamp(DATE_START, tz="UTC")) & \
       (df["ts"] <  pd.Timestamp(DATE_END,   tz="UTC"))

filtered = df[mask].drop(columns=["ts"])
filtered.to_csv(OUTPUT, index=False)
print(f"{len(filtered)} traces extraites → {OUTPUT}")
