# Exemples — traducteur xAPI → ProgSnap2

## Exemple 1 — `Run.Program` réussi

Entrée :

```json
[
  {
    "_id": {"$oid": "abc123"},
    "verb": {"id": "https://www.cristal.univ-lille.fr/verbs/Run.Program"},
    "actor": {"openid": "https://www.cristal.univ-lille.fr/users/alice/"},
    "timestamp": {"$date": "2024-05-10T12:00:00Z"},
    "object": {
      "extension": {
        "https://www.cristal.univ-lille.fr/objects/Program/CodeState": "print(\"hi\")"
      }
    },
    "result": {
      "success": true,
      "extension": {
        "https://www.cristal.univ-lille.fr/objects/Command/stdout": "hi\n",
        "https://www.cristal.univ-lille.fr/objects/Command/stderr": ""
      }
    }
  }
]
```

Effet attendu :

- `MainTable.csv` contient `EventID=abc123`, `EventType=Run.Program`, `ExecutionResult=Success`, `ProgramOutput=hi\n`.
- `CodeStates/CodeStates.csv` contient le code `print("hi")` et son `CodeStateID`.
- `LinkTables/Subject.csv` contient le lien entre `SubjectID` et `X-Identifier=alice`.

## Exemple 2 — ancien `Run.test`

Entrée :

```json
[
  {
    "verb": {"id": "https://www.cristal.univ-lille.fr/verbs/Run.test"},
    "actor": {"openid": "https://www.cristal.univ-lille.fr/users/bob/"},
    "timestamp": "2024-05-10T12:01:00Z",
    "object": {
      "extension": {
        "https://www.cristal.univ-lille.fr/objects/Tests/Tests": [
          {"name": "f1()", "status": true},
          {"name": "f2()", "status": false}
        ],
        "https://www.cristal.univ-lille.fr/objects/Tests/Status": false
      }
    }
  }
]
```

Effet attendu :

- le type source `Run.test` est écrit comme `Run.Test` ;
- `ExecutionResult=Error`, car `Tests/Status=false` ;
- `X-RunTestData` contient la liste des tests en JSON compact.

## Exemple 3 — événements de session et fichier

Les événements `Session.Start`, `File.Open`, `File.Save` et `Session.End` sont conservés. `File.Save` est écrit comme `X-File.Save`, car c'est un événement personnalisé par rapport au vocabulaire ProgSnap2 standard.
