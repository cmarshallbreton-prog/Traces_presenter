# Traducteur xAPI → ProgSnap2

### Auteur initial : Omar Kode Ousmane

## Vue d'ensemble

Ce projet traduit des traces xAPI issues de Thonny en fichiers CSV compatibles avec une organisation ProgSnap2.

Entrée :
- un fichier JSON contenant une liste de statements xAPI.

Sortie :
- `MainTable.csv`
- `CodeStates/CodeStates.csv`
- `LinkTables/Subject.csv`
- `DatasetMetadata.csv`

## Commande

```bash
python translator.py <input.json> -o <output_dir> [-sep ";"]
```

Exemple :

```bash
python translator.py CTP1-MI12.json -o sortieCTP1-MI12
```

`-o` accepte aussi un chemin explicite vers `MainTable.csv` pour garder la compatibilité avec l'ancienne interface.

## Tables générées

### MainTable.csv

| Colonne | Rôle |
| --- | --- |
| `EventID` | identifiant stable de l'événement, extrait de `_id.$oid` si possible |
| `EventType` | type ProgSnap2 canonique ou type personnalisé préfixé `X-` |
| `SubjectID` | identifiant anonymisé de l'utilisateur principal |
| `ToolInstances` | outil source, actuellement `Thonny` |
| `CodeStateID` | identifiant stable du code source associé |
| `ServerTimestamp` | horodatage du statement source |
| `SessionID` | identifiant de session extrait de `context.extension` |
| `ExecutionResult` | `Success` ou `Error` pour les exécutions |
| `ProgramInput` | réservé pour une entrée programme éventuelle |
| `ProgramOutput` | sortie standard capturée |
| `ProgramErrorOutput` | sortie d'erreur ou message d'erreur |
| `X-RunTestData` | données brutes des tests, sérialisées en JSON compact |
| `Lineno` | numéro de ligne pour les événements de débogage |

### CodeStates/CodeStates.csv

| Colonne | Rôle |
| --- | --- |
| `CodeStateID` | hash SHA256 du code normalisé |
| `Code` | contenu du code source extrait des statements |

### LinkTables/Subject.csv

| Colonne | Rôle |
| --- | --- |
| `SubjectID` | identifiant anonymisé stable |
| `X-Identifier` | identifiant utilisateur non anonymisé, à manipuler avec prudence |
| `X-TeamID` | identifiant complet du binôme/groupe quand l'`openid` contient plusieurs acteurs |

### DatasetMetadata.csv

Contient des propriétés de dataset, dont la version ProgSnap2 déclarée et le mode de représentation des CodeStates.

## Normalisation des événements

Le traducteur normalise les anciens noms xAPI suivants :

| Source xAPI | Sortie |
| --- | --- |
| `Run.test` | `Run.Test` |
| `Run.Debugger` | `Debug.Program` |
| `File.Save` | `X-File.Save` |
| `Run.Command` | `X-Run.Command` |
| `Docstring.Generate` | `X-Docstring.Generate` |

Les événements `Session.Start`, `Session.End`, `File.Open`, `Run.Program`, `Run.Test` et `Debug.Program` sont conservés.

## Règles importantes

- Les statements avec `research_usage: false` sont exclus.
- Les timestamps MongoDB `{ "$date": "..." }` sont acceptés.
- `stored` est utilisé comme fallback si `timestamp` est absent.
- Les extensions `stdout` et `stderr` sont lues sans sensibilité à la casse.
- Les états de code sont dédupliqués après normalisation des fins de ligne.

## Tests

```bash
PYTHONPATH=. pytest -q
```

La version corrigée a été validée avec `31 passed`.
