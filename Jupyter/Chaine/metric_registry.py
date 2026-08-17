"""Registre central des corpus et des indicateurs de la chaîne d'analyse.

Ce fichier est la source unique utilisée par les notebooks de génération.
Ajouter ou retirer un indicateur se fait ici.

Execution des scripts :

    python <script.py> <entrée> <sortie.csv> [arguments supplémentaires]

Toutes les sorties de métriques doivent contenir une colonne ``SubjectID`` et
une ou plusieurs colonnes numériques de métriques.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class MetricJob:
    """Description d'un script de métrique exécutable par le pipeline."""

    script: str
    output: str
    metric: str
    description: str
    required_columns: tuple[str, ...] = ()
    extra_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class DatasetSpec:
    """Configuration d'un corpus de traces."""

    name: str
    scripts_dir: str
    input_path: str
    input_is_directory: bool
    jobs: tuple[MetricJob, ...] = field(default_factory=tuple)

    def scripts_path(self, project_dir: Path) -> Path:
        return project_dir / self.scripts_dir

    def input(self, project_dir: Path) -> Path:
        return project_dir / self.input_path

    def csv_dir(self, project_dir: Path) -> Path:
        return project_dir / "csv" / self.name

    def log_dir(self, project_dir: Path) -> Path:
        return self.csv_dir(project_dir) / "logs"

    def analysis_dir(self, project_dir: Path) -> Path:
        return project_dir / "analysis" / self.name


def job(
    script: str,
    output: str,
    metric: str,
    description: str,
    required_columns: Sequence[str] = (),
    extra_args: Sequence[str] = (),
) -> MetricJob:

    return MetricJob(
        script=script,
        output=output,
        metric=metric,
        description=description,
        required_columns=tuple(required_columns),
        extra_args=tuple(str(arg) for arg in extra_args),
    )


# ---------------------------------------------------------------------------
# Mirabelle
# ---------------------------------------------------------------------------
MIRABELLE_JOBS = (
    job(
        "session_count_Mirabelle.py",
        "session_count.csv",
        "SessionCount",
        "Nombre de sessions d'activité séparées par plus de 5 minutes.",
        ["actor", "verb", "timestamp.$date"],
        ["5.0"],
    ),
    job(
        "session_span_Mirabelle.py",
        "session_span.csv",
        "SessionSpanMinutes",
        "Durée moyenne des sessions Run.Test séparées par plus de 5 minutes.",
        ["actor", "verb", "timestamp.$date"],
    ),
    job(
        "test_pass_rate_Mirabelle.py",
        "test_pass_rate.csv",
        "TestPassRate",
        "Proportion globale des cas de test étudiants qui réussissent.",
        ["actor", "verb", "tests"],
    ),
    job(
        "failed_run_ratio_Mirabelle.py",
        "failed_run_ratio.csv",
        "FailedTestRunRatio",
        "Part des Run.Test non vides contenant au moins un FailedVerdict.",
        ["actor", "verb", "tests"],
    ),
    job(
        "exception_run_ratio_Mirabelle.py",
        "exception_run_ratio.csv",
        "ExceptionTestRunRatio",
        "Part des Run.Test non vides contenant au moins un ExceptionVerdict.",
        ["actor", "verb", "tests"],
    ),
    job(
        "function_coverage_Mirabelle.py",
        "function_coverage.csv",
        "FunctionCoverage",
        "Nombre de fonctions considérées comme traitées.",
        ["actor", "verb", "tests", "P_codeState"],
    ),
    job(
        "eq_FE_Mirabelle.py",
        "error_quotient_fe.csv",
        "ErrorQuotient_FE",
        "Error Quotient, identité d'erreur au niveau du verdict.",
        ["actor", "verb", "tests", "timestamp.$date"],
    ),
    job(
        "eq_Mirabelle.py",
        "error_quotient.csv",
        "ErrorQuotient",
        "Error Quotient, identité d'erreur au niveau du message détaillé.",
        ["actor", "verb", "tests", "timestamp.$date"],
    ),
    job(
        "red_FE_Mirabelle.py",
        "red_fe.csv",
        "RED_FE",
        "Repeated Error Density, identité d'erreur au niveau du verdict.",
        ["actor", "verb", "tests", "timestamp.$date"],
    ),
    job(
        "red_Mirabelle.py",
        "red.csv",
        "RED",
        "Repeated Error Density, identité d'erreur au niveau du message détaillé.",
        ["actor", "verb", "tests", "timestamp.$date"],
    ),
    job(
        "attempts_to_first_success_Mirabelle.py",
        "attempts_to_first_success.csv",
        "AttemptsToFirstSuccess",
        "Nombre moyen de tentatives jusqu'au premier succès complet d'une fonction.",
        ["actor", "verb", "tests", "timestamp.$date"],
    ),
    job(
        "time_to_first_success_Mirabelle.py",
        "time_to_first_success.csv",
        "TimeToFirstSuccess",
        "Temps moyen en minutes jusqu'au premier succès complet d'une fonction.",
        ["actor", "verb", "tests", "timestamp.$date"],
    ),
    job(
        "first_attempt_success_rate_Mirabelle.py",
        "first_attempt_success_rate.csv",
        "FirstAttemptSuccessRate",
        "Part des fonctions réussies dès leur première tentative observée.",
        ["actor", "verb", "tests", "timestamp.$date"],
    ),
    job(
        "productive_transition_rate_Mirabelle.py",
        "productive_transition_rate.csv",
        "ProductiveTransitionRate",
        "Part des changements de code comparables qui améliorent le taux de tests réussis.",
        ["actor", "verb", "tests", "timestamp.$date", "P_codeState"],
    ),
    job(
        "code_change_magnitude_Mirabelle.py",
        "code_change_magnitude.csv",
        "CodeChangeMagnitude",
        "Amplitude moyenne normalisée des changements de code entre Run.Test.",
        ["actor", "verb", "tests", "timestamp.$date", "P_codeState"],
    ),
    job(
        "unchanged_rerun_ratio_Mirabelle.py",
        "unchanged_rerun_ratio.csv",
        "UnchangedRerunRatio",
        "Part des relances de tests consécutives sans changement de code.",
        ["actor", "verb", "tests", "timestamp.$date", "P_codeState"],
    ),
)


# ---------------------------------------------------------------------------
# Nowledgeable
# ---------------------------------------------------------------------------
NOWLEDGEABLE_JOBS = (
    job(
        "session_count_Nowledgeable.py",
        "session_count.csv",
        "SessionCount",
        "Nombre de sessions d'activité séparées par plus de 5 minutes.",
        ["studentId", "answeredAt"],
        ["5.0"],
    ),
    job(
        "test_pass_rate_Nowledgeable.py",
        "test_pass_rate.csv",
        "TestPassRate",
        "Proportion des cas de test enseignants réussis.",
        ["studentId", "recordedFeedback"],
    ),
    job(
        "total_test_count_Nowledgeable.py",
        "total_test_count.csv",
        "TotalTestCount",
        "Nombre total d'exécutions de cas de test détaillés.",
        ["studentId", "recordedFeedback"],
    ),
    job(
        "exercise_coverage_Nowledgeable.py",
        "exercise_coverage.csv",
        "ExerciseCoverage",
        "Nombre d'exercices considérés comme traités.",
        ["studentId", "exerciceId", "answerScore", "answerContent"],
    ),
    job(
        "function_coverage_Nowledgeable.py",
        "function_coverage.csv",
        "FunctionCoverage",
        "Nombre de fonctions C/C++ considérées comme traitées.",
        ["studentId", "exerciceId", "answerScore", "answerContent"],
    ),
    job(
        "score_progression_Nowledgeable.py",
        "score_progression.csv",
        "ScoreProgression",
        "Progression moyenne entre le premier et le dernier score par exercice.",
        ["studentId", "exerciceId", "answeredAt", "answerScore"],
    ),
    job(
        "max_unchanged_code_attempts_Nowledgeable.py",
        "max_unchanged_code_attempts.csv",
        "MaxUnchangedCodeAttempts",
        "Plus longue série de soumissions consécutives avec code identique.",
        ["studentId", "exerciceId", "answeredAt", "answerContent"],
    ),
    job(
        "eq_Nowledgeable.py",
        "error_quotient.csv",
        "ErrorQuotient",
        "Error Quotient calculé sur les diagnostics de compilation normalisés.",
        ["studentId", "exerciceId", "answeredAt", "recordedFeedback"],
    ),
    job(
        "red_Nowledgeable.py",
        "red.csv",
        "RED",
        "Repeated Error Density sur les diagnostics de compilation normalisés.",
        ["studentId", "exerciceId", "answeredAt", "recordedFeedback"],
    ),
    job(
        "attempts_to_first_success_Nowledgeable.py",
        "attempts_to_first_success.csv",
        "AttemptsToFirstSuccess",
        "Nombre moyen de tentatives jusqu'au premier exercice entièrement correct.",
        ["studentId", "exerciceId", "answeredAt", "answerIsRight"],
    ),
    job(
        "time_to_first_success_Nowledgeable.py",
        "time_to_first_success.csv",
        "TimeToFirstSuccess",
        "Temps moyen en minutes jusqu'au premier exercice entièrement correct.",
        ["studentId", "exerciceId", "answeredAt", "answerIsRight"],
    ),
    job(
        "first_attempt_success_rate_Nowledgeable.py",
        "first_attempt_success_rate.csv",
        "FirstAttemptSuccessRate",
        "Part des exercices entièrement corrects dès la première tentative.",
        ["studentId", "exerciceId", "answeredAt", "answerIsRight"],
    ),
    job(
        "productive_transition_rate_Nowledgeable.py",
        "productive_transition_rate.csv",
        "ProductiveTransitionRate",
        "Part des changements de code qui augmentent answerScore.",
        ["studentId", "exerciceId", "answeredAt", "answerScore", "answerContent"],
    ),
    job(
        "code_change_magnitude_Nowledgeable.py",
        "code_change_magnitude.csv",
        "CodeChangeMagnitude",
        "Amplitude moyenne normalisée des changements de code.",
        ["studentId", "exerciceId", "answeredAt", "answerContent"],
    ),
    job(
        "unchanged_rerun_ratio_Nowledgeable.py",
        "unchanged_rerun_ratio.csv",
        "UnchangedRerunRatio",
        "Part des soumissions consécutives d'un exercice avec code identique.",
        ["studentId", "exerciceId", "answeredAt", "answerContent"],
    ),
)


# ---------------------------------------------------------------------------
# ProgSnap2
# ---------------------------------------------------------------------------

PROGSNAP2_JOBS = (
    job("compile_count.py", "compile_count.csv", "CompileCount", "Nombre moyen de compilations par session filtrée."),
    job("compile_span.py", "compile_span.csv", "CompileSpanMinutes", "Durée moyenne des épisodes de compilation par session filtrée."),
    job("compil_ratio.py", "compile_success_rate.csv", "CompileSuccessRate", "Taux moyen de compilations réussies par session filtrée."),
    job("first_compile_vs_global_first.py", "first_compile_vs_global_first.csv", "MinutesFromGlobalFirstCompile", "Décalage de la première compilation d'une session par rapport à la première compilation du corpus."),
    job("last_compile_vs_global_last.py", "last_compile_vs_global_last.csv", "MinutesToGlobalLastCompile", "Décalage de la dernière compilation d'une session par rapport à la dernière compilation du corpus."),
    job("frac_long.py", "fraction_long_gaps.csv", "FracLong", "Fraction moyenne des intervalles > 5 minutes entre compilations d'une session.", extra_args=["5.0"]),
    job("session_count.py", "session_count.csv", "SessionCount", "Nombre moyen de sous-sessions de compilation par session ProgSnap2.", extra_args=["5.0"]),
    job("mean_test_score.py", "mean_test_score.csv", "MeanTestScore", "Score moyen des événements de test/exécution par session."),
    job("time_to_score1.py", "time_to_score1.csv", "MinutesToScore1", "Temps moyen d'une session jusqu'au premier score égal à 1, plafonné à 60 min si jamais atteint."),
    job("eq.py", "error_quotient.csv", "ErrorQuotient", "Error Quotient original appliqué aux erreurs de compilation ProgSnap2."),
    job("red.py", "red.csv", "RED", "Repeated Error Density originale appliquée aux erreurs de compilation ProgSnap2."),
    job(
        "watwin.py",
        "watwin.csv",
        "WatWin",
        "Score WatWin fondé sur répétition d'erreurs et temps de correction.",
        ["SourceLocation"],
    ),
)


DATASETS: dict[str, DatasetSpec] = {
    "Mirabelle": DatasetSpec(
        name="Mirabelle",
        scripts_dir="scripts_Mirabelle",
        input_path="data/donnees_2024-09-20_10h15-11h45.csv",
        input_is_directory=False,
        jobs=MIRABELLE_JOBS,
    ),
    "Nowledgeable": DatasetSpec(
        name="Nowledgeable",
        scripts_dir="scripts_Nowledgeable",
        input_path="data/session_13568_answers_corrige.csv",
        input_is_directory=False,
        jobs=NOWLEDGEABLE_JOBS,
    ),
    "Progsnap2": DatasetSpec(
        name="Progsnap2",
        scripts_dir="scripts_Progsnap2",
        input_path="data",
        input_is_directory=True,
        jobs=PROGSNAP2_JOBS,
    ),
}


def get_dataset(name: str) -> DatasetSpec:
    """Retourne la configuration d'un corpus."""

    try:
        return DATASETS[name]
    except KeyError as exc:
        choices = ", ".join(DATASETS)
        raise ValueError(f"Corpus inconnu : {name!r}. Valeurs possibles : {choices}") from exc
