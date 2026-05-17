Notebooks ajoutés
=================

01_generer_csv.ipynb
- À lancer depuis la racine du dossier Chaine.
- Exécute les scripts dans scripts/ pour régénérer les CSV de métriques dans csv/.
- Produit aussi csv/run_report.csv et des journaux dans csv/logs/.
- Watwin est ignoré automatiquement si la colonne SourceLocation est absente de MainTable.csv.

02_acp_analyse.ipynb
- À lancer après le premier notebook, ou avec les CSV déjà présents dans csv/.
- Agrège les CSV de métriques par SubjectID.
- Réalise une ACP et sauvegarde les résultats dans analysis/.

Dépendances principales : pandas, numpy, scikit-learn, matplotlib, jupyter.
