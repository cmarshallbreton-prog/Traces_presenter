"""Fonctions partagées par les notebooks de génération et d'analyse.

Le but est d'éviter les trois implémentations légèrement différentes qui
existaient auparavant dans les notebooks Mirabelle, Nowledgeable et ProgSnap2.
"""

from __future__ import annotations

from dataclasses import asdict
from functools import reduce
from pathlib import Path
import subprocess
import sys
from typing import Iterable

import pandas as pd

from metric_registry import DatasetSpec, MetricJob, get_dataset


REPORT_FILENAMES = {"run_report.csv", "stats.csv"}


def detect_project_dir(start: Path | None = None) -> Path:
    """Détecte la racine du projet depuis un notebook ou un terminal."""

    start = (start or Path.cwd()).resolve()
    candidates = [start, start / "Chaine", start.parent, start.parent / "Chaine"]
    for candidate in candidates:
        if (candidate / "metric_registry.py").exists() and (candidate / "data").exists():
            return candidate.resolve()
    raise FileNotFoundError(
        "Impossible de détecter la racine du projet. "
        "Placez-vous dans Chaine/ ou renseignez PROJECT_DIR manuellement."
    )


def dataset_input_file(project_dir: Path, spec: DatasetSpec, input_override: Path | None = None) -> Path:
    """Retourne le fichier physique à inspecter pour un corpus."""

    source = input_override.resolve() if input_override is not None else spec.input(project_dir)
    if spec.input_is_directory:
        return source / "MainTable.csv"
    return source


def inspect_input(
    project_dir: Path,
    spec: DatasetSpec,
    input_override: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Charge l'entrée et retourne ``(table, résumé)`` pour le notebook."""

    input_file = dataset_input_file(project_dir, spec, input_override)
    if not input_file.exists():
        raise FileNotFoundError(f"Fichier d'entrée introuvable : {input_file}")

    # Le moteur Python est utile pour Mirabelle ; il reste compatible avec les
    # deux autres fichiers et rend la lecture homogène dans les notebooks.
    df = pd.read_csv(input_file, on_bad_lines="skip", engine="python")

    id_candidates = ["SubjectID", "actor", "studentId"]
    id_col = next((col for col in id_candidates if col in df.columns), None)
    summary = pd.DataFrame([
        {
            "corpus": spec.name,
            "fichier": input_file.name,
            "lignes": int(df.shape[0]),
            "colonnes": int(df.shape[1]),
            "sujets_uniques": int(df[id_col].nunique()) if id_col else None,
            "colonne_identifiant": id_col,
        }
    ])
    return df, summary


def missing_columns(job: MetricJob, columns: Iterable[str]) -> list[str]:
    """Colonnes brutes absentes pour un job, d'après le registre."""

    available = set(columns)
    return [column for column in job.required_columns if column not in available]


def validate_metric_output(df: pd.DataFrame, job: MetricJob) -> list[str]:
    """Retourne les incohérences de schéma d'un CSV de métrique."""

    errors: list[str] = []
    if "SubjectID" not in df.columns:
        errors.append("colonne SubjectID absente")
    if job.metric not in df.columns:
        errors.append(f"colonne de métrique attendue absente : {job.metric}")
    if errors:
        return errors

    if df["SubjectID"].isna().any():
        errors.append("SubjectID contient des valeurs manquantes")
    if df["SubjectID"].duplicated().any():
        duplicate_count = int(df["SubjectID"].duplicated(keep=False).sum())
        errors.append(f"SubjectID dupliqué ({duplicate_count} ligne(s) concernée(s))")

    metric_values = df[job.metric]
    numeric = pd.to_numeric(metric_values, errors="coerce")
    invalid_numeric = metric_values.notna() & numeric.isna()
    if invalid_numeric.any():
        errors.append(f"{job.metric} contient des valeurs non numériques")
    return errors


def _remove_stale_output(path: Path) -> None:
    """Supprime une sortie qui ne doit pas être agrégée comme résultat courant."""

    try:
        path.unlink(missing_ok=True)
    except TypeError:  # compatibilité Python < 3.8
        if path.exists():
            path.unlink()


def run_metric_jobs(
    project_dir: Path,
    dataset_name: str,
    *,
    overwrite: bool = True,
    precheck_columns: bool = True,
    input_override: Path | None = None,
) -> pd.DataFrame:
    """Exécute tous les scripts d'un corpus dans des sous-processus isolés.

    Un sous-processus par indicateur évite que les imports, loggers et ``sys.argv``
    d'un script contaminent les suivants. La sortie standard et la sortie
    d'erreur sont réunies dans ``csv/<corpus>/logs/<script>.log``.
    """

    spec = get_dataset(dataset_name)
    scripts_dir = spec.scripts_path(project_dir)
    input_path = input_override.resolve() if input_override is not None else spec.input(project_dir)
    input_file = dataset_input_file(project_dir, spec, input_override)
    csv_dir = spec.csv_dir(project_dir)
    log_dir = spec.log_dir(project_dir)

    if not scripts_dir.exists():
        raise FileNotFoundError(f"Dossier de scripts introuvable : {scripts_dir}")
    if not input_path.exists() or not input_file.exists():
        raise FileNotFoundError(f"Entrée du corpus introuvable : {input_path}")

    csv_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    raw_columns: set[str] = set()
    if precheck_columns:
        # Même pour ProgSnap2, on peut vérifier les colonnes du MainTable brut.
        # Les jobs historiques qui dépendent de colonnes créées par data_filter
        # laissent simplement required_columns vide dans le registre.
        raw_columns = set(pd.read_csv(input_file, nrows=0).columns)

    report: list[dict[str, object]] = []
    for metric_job in spec.jobs:
        script_path = scripts_dir / metric_job.script
        output_path = csv_dir / metric_job.output
        log_path = log_dir / f"{Path(metric_job.script).stem}.log"

        row: dict[str, object] = {
            **asdict(metric_job),
            "status": None,
            "returncode": None,
            "rows": None,
            "columns": None,
            "output_path": str(output_path),
            "log_path": str(log_path),
            "message": "",
        }

        # ``overwrite=False`` signifie réellement "réutiliser l'existant" :
        # on ne relance pas un script qui écraserait de toute façon son CSV.
        if not overwrite and output_path.exists():
            try:
                existing = pd.read_csv(output_path)
                validation_errors = validate_metric_output(existing, metric_job)
                if validation_errors:
                    row.update(
                        status="invalid_existing",
                        rows=int(existing.shape[0]),
                        columns=", ".join(existing.columns.astype(str)),
                        message="; ".join(validation_errors),
                    )
                else:
                    row.update(
                        status="skipped_existing",
                        rows=int(existing.shape[0]),
                        columns=", ".join(existing.columns.astype(str)),
                        message="CSV existant réutilisé (overwrite=False)",
                    )
            except Exception as exc:
                row.update(status="invalid_existing", message=f"CSV existant illisible : {exc}")
            report.append(row)
            continue

        # En mode normal (overwrite=True), l'ancienne sortie est supprimée AVANT
        # tout précontrôle afin qu'un échec ne laisse jamais une métrique obsolète.
        if overwrite:
            _remove_stale_output(output_path)

        if not script_path.exists():
            row.update(status="missing_script", message=f"Script introuvable : {script_path}")
            report.append(row)
            continue

        # Pour ProgSnap2, data_filter peut créer SessionID et filtrer la table
        # avant que les scripts ne vérifient leurs colonnes : on laisse donc les
        # scripts historiques effectuer eux-mêmes cette validation.
        if raw_columns and metric_job.required_columns:
            missing = missing_columns(metric_job, raw_columns)
            if missing:
                row.update(status="missing_columns", message=f"Colonnes manquantes : {missing}")
                report.append(row)
                continue

        command = [
            sys.executable,
            str(script_path),
            str(input_path),
            str(output_path),
            *metric_job.extra_args,
        ]
        completed = subprocess.run(
            command,
            cwd=project_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        log_path.write_text(
            "COMMANDE\n" + " ".join(command) + "\n\n"
            + "STDOUT\n" + completed.stdout + "\n\n"
            + "STDERR\n" + completed.stderr,
            encoding="utf-8",
        )

        row["returncode"] = completed.returncode
        if completed.returncode != 0:
            _remove_stale_output(output_path)
            row.update(status="error", message="Le script s'est terminé en erreur ; voir le journal.")
        elif not output_path.exists():
            row.update(status="no_output", message="Le script n'a produit aucun CSV.")
        else:
            try:
                produced = pd.read_csv(output_path)
                validation_errors = validate_metric_output(produced, metric_job)
                if validation_errors:
                    _remove_stale_output(output_path)
                    row.update(
                        status="invalid_output",
                        rows=int(produced.shape[0]),
                        columns=", ".join(produced.columns.astype(str)),
                        message="; ".join(validation_errors),
                    )
                else:
                    row.update(
                        status="ok",
                        rows=int(produced.shape[0]),
                        columns=", ".join(produced.columns.astype(str)),
                        message="CSV produit et validé",
                    )
            except Exception as exc:  # pragma: no cover - garde-fou notebook
                _remove_stale_output(output_path)
                row.update(status="invalid_output", message=f"CSV illisible : {exc}")

        report.append(row)

    report_df = pd.DataFrame(report)
    report_df.to_csv(log_dir / "run_report.csv", index=False)
    return report_df


def metric_inventory(csv_dir: Path) -> pd.DataFrame:
    """Inventorie les CSV de métriques présents dans un dossier de corpus."""

    rows: list[dict[str, object]] = []
    if not csv_dir.exists():
        return pd.DataFrame(rows)

    for path in sorted(csv_dir.glob("*.csv")):
        if path.name.lower() in REPORT_FILENAMES:
            continue
        try:
            df = pd.read_csv(path)
            status = "ok" if "SubjectID" in df.columns else "sans SubjectID"
            rows.append({
                "fichier": path.name,
                "statut": status,
                "lignes": int(df.shape[0]),
                "colonnes": int(df.shape[1]),
                "variables": ", ".join(str(c) for c in df.columns if c != "SubjectID"),
            })
        except Exception as exc:
            rows.append({
                "fichier": path.name,
                "statut": f"illisible : {type(exc).__name__}",
                "lignes": None,
                "colonnes": None,
                "variables": "",
            })
    return pd.DataFrame(rows)


def aggregate_metrics(csv_dir: Path, join_mode: str = "outer") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Agrège les CSV d'un seul corpus en une table ``SubjectID × variables``.

    Contrairement à l'ancienne version, les collisions de noms de variables ne
    sont pas renommées silencieusement : elles provoquent une erreur explicite,
    car elles signalent presque toujours une incohérence de pipeline.
    """

    if join_mode not in {"outer", "inner"}:
        raise ValueError("join_mode doit valoir 'outer' ou 'inner'.")
    if not csv_dir.exists():
        raise FileNotFoundError(f"Dossier CSV introuvable : {csv_dir}")

    tables: list[pd.DataFrame] = []
    inventory_rows: list[dict[str, object]] = []
    seen_features: set[str] = set()

    for path in sorted(csv_dir.glob("*.csv")):
        if path.name.lower() in REPORT_FILENAMES:
            continue
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            inventory_rows.append({"fichier": path.name, "statut": "ignoré", "raison": str(exc)})
            continue

        if "SubjectID" not in df.columns:
            inventory_rows.append({"fichier": path.name, "statut": "ignoré", "raison": "SubjectID absent"})
            continue

        if df["SubjectID"].isna().any():
            raise ValueError(f"SubjectID manquant dans {path.name}")
        if df["SubjectID"].duplicated().any():
            duplicates = df.loc[df["SubjectID"].duplicated(keep=False), "SubjectID"].astype(str).unique()
            preview = ", ".join(duplicates[:5])
            raise ValueError(
                f"SubjectID dupliqué dans {path.name} ({len(duplicates)} sujet(s), ex. {preview})."
            )
        df = df.copy()
        feature_cols = [col for col in df.columns if col != "SubjectID"]
        collisions = sorted(seen_features.intersection(feature_cols))
        if collisions:
            raise ValueError(
                f"Collision de variables dans {path.name} : {collisions}. "
                "Corrigez le registre ou les scripts plutôt que de renommer implicitement."
            )
        seen_features.update(feature_cols)
        tables.append(df[["SubjectID", *feature_cols]])
        inventory_rows.append({
            "fichier": path.name,
            "statut": "chargé",
            "raison": "",
            "lignes": int(df.shape[0]),
            "variables": ", ".join(feature_cols),
        })

    if not tables:
        raise ValueError(f"Aucun CSV de métrique exploitable dans {csv_dir}")

    features = reduce(lambda left, right: pd.merge(left, right, on="SubjectID", how=join_mode), tables)
    return features, pd.DataFrame(inventory_rows)


def prepare_numeric_features(
    features: pd.DataFrame,
    *,
    drop_features: Iterable[str] = (),
    min_non_null_features: int = 2,
) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    """Nettoie une table agrégée avant ACP ou K-means.

    Retourne ``(X_raw, variables_utilisables, variables_supprimees)``.
    """

    data = features.copy()
    for col in data.columns:
        if col != "SubjectID":
            data[col] = pd.to_numeric(data[col], errors="coerce")

    existing_drop = [col for col in drop_features if col in data.columns]
    if existing_drop:
        data = data.drop(columns=existing_drop)

    numeric_cols = [
        col for col in data.columns
        if col != "SubjectID" and pd.api.types.is_numeric_dtype(data[col])
    ]
    if not numeric_cols:
        raise ValueError("Aucune variable numérique disponible.")

    non_null = data[numeric_cols].notna().sum(axis=1)
    x_raw = data.loc[non_null >= min_non_null_features, ["SubjectID", *numeric_cols]].reset_index(drop=True)

    usable: list[str] = []
    removed: list[dict[str, str]] = []
    for col in numeric_cols:
        series = x_raw[col]
        if series.notna().sum() == 0:
            removed.append({"variable": col, "raison": "entièrement vide"})
        elif series.nunique(dropna=True) <= 1:
            removed.append({"variable": col, "raison": "constante"})
        else:
            usable.append(col)

    x_raw = x_raw[["SubjectID", *usable]]
    return x_raw, usable, pd.DataFrame(removed)
