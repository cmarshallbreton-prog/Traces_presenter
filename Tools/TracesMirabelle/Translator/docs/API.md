# Référence API

## `translator.py`

### `main(argv: list[str] | None = None) -> None`

Point d'entrée CLI.

- Parse les arguments de ligne de commande.
- Appelle la traduction du fichier d'entrée.
- `-o` désigne un dossier de sortie ou un chemin explicite vers `MainTable.csv`.
- `-sep` / `--separator` permet de choisir le séparateur CSV.

### `translate_file(input_path: Path, output_main_path: Path, delimiter: str = ',') -> tuple[Path, Path, Path]`

Traduit un fichier JSON xAPI et écrit les fichiers ProgSnap2.

Paramètres :

- `input_path` : fichier JSON source.
- `output_main_path` : chemin complet du fichier `MainTable.csv`.
- `delimiter` : séparateur utilisé pour les fichiers CSV.

Retour :

- chemin de `MainTable.csv` ;
- chemin de `LinkTables/Subject.csv` ;
- chemin de `CodeStates/CodeStates.csv`.

La fonction écrit aussi `DatasetMetadata.csv`, mais ne le retourne pas pour conserver une API simple et compatible avec l'ancienne forme à trois valeurs.

## `src/xapi_progsnap2_translator/io.py`

### `read_xapi_json(path: Path) -> list[Statement]`

Lit un fichier JSON contenant une liste de statements xAPI.

### `write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]], delimiter: str = ',') -> None`

Écrit un CSV avec en-têtes explicites.

## `src/xapi_progsnap2_translator/main_table.py`

Fonctions utiles :

- `extract_session_id(statement)` : lit `SessionID` depuis `context.extension`.
- `extract_success(statement)` : lit `result.success`.
- `extract_output_error(statement)` : lit `stdout` et `stderr` sans sensibilité à la casse.
- `extract_lineno(statement)` : lit le numéro de ligne pour les événements de débogage.
- `extract_run_test_data(statement)` : sérialise les tests en JSON compact.
- `translate_statements_to_main_rows(statements)` : convertit une liste de statements en lignes de `MainTable.csv`.

## `src/xapi_progsnap2_translator/link_table.py`

- `get_anonymized_subject_id(statement)` : calcule l'identifiant anonymisé.
- `get_identifier(statement)` : extrait l'identifiant utilisateur non anonymisé.
- `get_team_id(statement)` : extrait le binôme/groupe complet si présent.
- `translate_statements_to_link_rows(statements)` : construit `LinkTables/Subject.csv`.

## `src/xapi_progsnap2_translator/code_states.py`

- `compute_code_states_id(code_state)` : calcule l'identifiant stable d'un état de code.
- `extract_code_state(statement)` : lit le code source depuis le statement.
- `translate_statements_to_code_states_rows(statements)` : construit `CodeStates/CodeStates.csv`.

## `src/xapi_progsnap2_translator/utils.py`

Utilitaires principaux :

- `get_event_type(statement)` : retourne le type d'événement normalisé.
- `extract_event_id(statement, fallback_index)` : extrait un `EventID` stable.
- `coerce_xapi_date(value)` : accepte les chaînes et les dates MongoDB `{ "$date": "..." }`.
- `is_research_usable(statement)` : applique le filtre `research_usage`.
- `extract_primary_user_from_openid(openid)`.
- `normalize_newlines(text)`.
- `sha256_hex(text)`.
- `coerce_cell_text(value)`.
