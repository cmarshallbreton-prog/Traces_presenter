import sys

import utils_Mirabelle as um

out = um.out


def calculate_eq(actor_attempts) -> float | None:
    """
    Calcule l'Error Quotient d'un étudiant à partir de la table de ses
    tentatives (issue de verdict_utils.build_attempts).

    Retourne un float dans [0.0, 1.0], ou None si aucune paire de
    tentatives consécutives n'est disponible.
    """
    pairs = um.extract_attempt_pairs(actor_attempts)
    if len(pairs) == 0:
        return None

    total_score = 0.0
    for e1_idx, e2_idx in pairs:
        e1_errors = actor_attempts["error_categories"].iloc[e1_idx]
        e2_errors = actor_attempts["error_categories"].iloc[e2_idx]

        score_delta = 0
        if len(e1_errors) > 0 and len(e2_errors) > 0:
            # Les deux tentatives ont produit une erreur
            score_delta += 8
            # Partagent-elles au moins une catégorie d'erreur ?
            if len(e1_errors & e2_errors) > 0:
                score_delta += 3

        total_score += score_delta / 11

    return total_score / len(pairs)


def load_csv(path: str):
    return um.load_csv(path)


def main(read_path: str, write_path: str) -> None:
    df = um.load_csv(read_path)

    if not um.check_columns(df, um.REQUIRED_COLS):
        sys.exit(1)

    actors = df[um.COL_ACTOR].dropna().unique()
    out.info("%d étudiant(s) trouvé(s)", len(actors))

    metric_map: dict[str, float] = {}
    dropped = 0

    for actor in sorted(actors):
        actor_rows = df[df[um.COL_ACTOR] == actor]
        attempts = um.build_attempts(actor_rows)
        eq = calculate_eq(attempts)

        if eq is None:
            out.warning("  %s : pas de paire de tentatives exploitable — ignoré", actor)
            dropped += 1
        else:
            metric_map[actor] = round(eq, 6)
            out.info("  %s : EQ = %.3f  (%d Run.Test)", actor, eq, len(attempts))

    out.info("%d étudiant(s) ignoré(s) (pas de paire de tentatives exploitable)", dropped)
    um.write_metric("ErrorQuotient_FE", metric_map, write_path)


if __name__ == "__main__":
    _read = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    _write = sys.argv[2] if len(sys.argv) > 2 else "out/ErrorQuotient.csv"
    main(_read, _write)
