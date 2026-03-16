import pandas as pd
import matplotlib.pyplot as plt
from PyComplexHeatmap import *

# 1) Charger les données
df = pd.read_excel("Notes EQ RED.xlsx", sheet_name="Récap")
df = df.dropna(subset=["SubjectID"]).copy()

metrics = [
    "EQ", "RED", "Comp_Count", "Sess_Count", "Comp_FP_Ratio",
    "Frac_Long", "Mean_Test", "First_Compile", "Compile_Span",
    "Last_Compile", "Time_To_Score1"
]

# 2) Matrice principale
X = df.set_index("SubjectID")[metrics].astype(float)
Xz = (X - X.mean()) / X.std()

# 3) Annotations de lignes
row_meta = df.set_index("SubjectID")[["Catégorie", "Notes"]]

row_ha = HeatmapAnnotation(
    Catégorie=anno_simple(row_meta["Catégorie"], cmap="Set2"),
    Note=anno_simple(row_meta["Notes"], cmap="viridis"),
    axis=0,
    verbose=0
)

# 4) Clustermap
plt.figure(figsize=(10, 14))
cm = ClusterMapPlotter(
    data=Xz,
    right_annotation=row_ha,
    row_split=row_meta["Catégorie"],
    row_cluster=True,
    col_cluster=True,
    show_rownames=False,
    cmap="RdBu_r",
    center=0,
    label="z-score",
    verbose=0
)

plt.show()