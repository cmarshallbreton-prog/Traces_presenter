import sys

import utils_Mirabelle as um

out = um.out


def calculate_red(actor_attempts) -> float | None:
    """
    Calcule la Repeated Error Density d'un étudiant à partir de la table
    de ses tentatives (issue de verdict_utils.build_attempts).

    Retourne un float >= 0.0, ou None si aucune paire de tentatives
    consécutives n'est disponible.
    """
    red = 0.0
    divisor = 0

    for segment in um.get_segments_indexes(actor_attempts):
        repeated = 0
        for i in range(1, len(segment)):
            divisor += 1
            e1_errors = actor_attempts["error_categories"].iloc[segment[i - 1]]
            e2_errors = actor_attempts["error_categories"].iloc[segment[i]]
            shared_errors = e1_errors & e2_errors

            if len(shared_errors) > 0:
                # Erreur répétée : on prolonge la série en cours
                repeated += 1
            else:
                # Nouvelle erreur, ou pas d'erreur : on clôt la série en
                # cours (si elle existe) et on la remet à zéro
                if repeated > 0:
                    red += (repeated ** 2) / (repeated + 1)
                repeated = 0

        if repeated > 0:
            red += (repeated ** 2) / (repeated + 1)

    if divisor == 0:
        return None

    return red / divisor


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
        red = calculate_red(attempts)

        if red is None:
            out.warning("  %s : pas de paire de tentatives exploitable — ignoré", actor)
            dropped += 1
        else:
            metric_map[actor] = round(red, 6)
            out.info("  %s : RED = %.3f  (%d Run.Test)", actor, red, len(attempts))

    out.info("%d étudiant(s) ignoré(s) (pas de paire de tentatives exploitable)", dropped)
    um.write_metric("RED_FE", metric_map, write_path)


if __name__ == "__main__":
    _read = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    _write = sys.argv[2] if len(sys.argv) > 2 else "out/RED.csv"
    main(_read, _write)
