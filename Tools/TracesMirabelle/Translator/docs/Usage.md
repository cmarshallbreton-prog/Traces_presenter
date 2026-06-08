# Usage et ligne de commande

## Commande principale

```bash
python translator.py <input.json> -o <output_dir> -sep ";"
```

Les options `-o` et `-sep` sont optionnelles et leur ordre n'a pas d'importance.

Exemple :

```bash
python translator.py CTP1-MI12.json -o sortieCTP1-MI12
```

Le traducteur écrit :

- `sortieCTP1-MI12/MainTable.csv`
- `sortieCTP1-MI12/CodeStates/CodeStates.csv`
- `sortieCTP1-MI12/LinkTables/Subject.csv`
- `sortieCTP1-MI12/DatasetMetadata.csv`

`-o` peut aussi recevoir un chemin direct vers `MainTable.csv` :

```bash
python translator.py input.json -o out/MainTable.csv
```

## Options disponibles

- `input` : chemin vers un fichier JSON contenant une liste de statements xAPI.
- `-o` : dossier de sortie, ou chemin explicite vers `MainTable.csv`.
- `-sep`, `--separator` : séparateur CSV, `,` par défaut.

## Format attendu en entrée

Le fichier d'entrée doit contenir un tableau JSON à la racine. Chaque élément du tableau doit être un objet représentant un statement xAPI.

Les statements avec `research_usage: false` sont ignorés. Si `research_usage` est absent, le statement est conservé.

## Événements conservés

- `Run.Program`
- `Run.test`, normalisé en `Run.Test`
- `Run.Debugger`, normalisé en `Debug.Program`
- `Session.Start`
- `Session.End`
- `File.Open`
- `File.Save`, conservé comme `X-File.Save`
- `Run.Command`, conservé comme `X-Run.Command`
- `Docstring.Generate`, conservé comme `X-Docstring.Generate`

## Comportement des colonnes

- `ExecutionResult` vaut `Success` ou `Error` quand `result.success` ou un statut de test est disponible.
- `ProgramOutput` contient `stdout`.
- `ProgramErrorOutput` contient `stderr` ou l'erreur de test.
- `X-RunTestData` contient une liste JSON compacte pour les événements `Run.Test`.
- `CodeStateID` référence `CodeStates/CodeStates.csv` quand un état de code est disponible.
- `SessionID` remplace l'ancien nom fautif `Session.Id`.

## Tests

```bash
PYTHONPATH=. pytest -q
```
