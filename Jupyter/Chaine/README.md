# Chaîne d’analyse des traces de programmation

Cette version nettoyée regroupe les traitements de trois corpus de traces :

- **Mirabelle** : les étudiants écrivent eux-mêmes les tests qu’ils exécutent ;
- **Nowledgeable** : les tests et le barème sont fixés par les enseignants ;
- **ProgSnap2** : traces au format ProgSnap2, principalement centrées ici sur les compilations, erreurs et scores d’exécution.

L’objectif du nettoyage est de rendre la chaîne reproductible et lisible : mêmes conventions de sortie, un registre central des indicateurs, des notebooks qui ne mélangent plus les corpus, et des scripts documentés.

> **Contrainte de conservation.** Les fichiers `scripts_Progsnap2/eq.py`, `scripts_Progsnap2/red.py` et `scripts_Progsnap2/watwin.py` n’ont pas été modifiés. Leur comportement historique est conservé tel quel.

---

## 1. Organisation du projet

```text
Chaine/
├── data/
│   ├── traces_20_sept_10_11.csv
│   ├── session_13568_answers_corrige.csv
│   └── MainTable.csv
├── scripts_Mirabelle/
├── scripts_Nowledgeable/
├── scripts_Progsnap2/
├── csv/
│   ├── Mirabelle/
│   ├── Nowledgeable/
│   └── Progsnap2/
├── analysis/
│   ├── Mirabelle/
│   ├── Nowledgeable/
│   └── Progsnap2/
├── metric_registry.py
├── pipeline_utils.py
├── 01_generer_csv_Mirabelle.ipynb
├── 01_generer_csv_Nowledgeable.ipynb
├── 01_generer_csv_Progsnap2.ipynb
├── 01b_recap_donnees.ipynb
├── 02_acp_analyse.ipynb
└── 02_kmeans_analyse.ipynb
```

### Registre central

`metric_registry.py` constitue la source unique de configuration. Il indique, pour chaque corpus :

- le fichier ou dossier d’entrée ;
- le dossier de scripts ;
- les scripts à lancer ;
- le nom du CSV produit ;
- la variable attendue ;
- les champs requis ;
- les éventuels arguments supplémentaires.

Il n’est donc plus nécessaire de maintenir trois listes de scripts différentes dans les notebooks.

### Exécution isolée

`pipeline_utils.py` lance chaque indicateur dans un **sous-processus Python séparé**. Cela évite les collisions de variables globales, de loggers, d’imports et de `sys.argv` entre scripts historiques.

Chaque exécution produit :

- un CSV dans `csv/<Corpus>/` ;
- un journal dans `csv/<Corpus>/logs/` ;
- un `run_report.csv` récapitulant les succès, erreurs et colonnes manquantes.

---

## 2. Ordre d’utilisation recommandé

### Étape 1 — Générer les métriques

Exécuter le notebook correspondant au corpus :

- `01_generer_csv_Mirabelle.ipynb`
- `01_generer_csv_Nowledgeable.ipynb`
- `01_generer_csv_Progsnap2.ipynb`

Chaque notebook possède la même structure. `INPUT_OVERRIDE = None` utilise le fichier déclaré dans `metric_registry.py`. Il est possible de fournir un autre CSV sans modifier les scripts.

### Étape 2 — Vérifier les données

Dans `01b_recap_donnees.ipynb`, régler :

```python
DATASET = "Mirabelle"
```

avec l’une des valeurs `"Mirabelle"`, `"Nowledgeable"` ou `"Progsnap2"`.

Le notebook fusionne **uniquement les métriques du corpus choisi**, par `SubjectID`, puis affiche les valeurs manquantes et les statistiques descriptives.

### Étape 3 — ACP

Même principe dans `02_acp_analyse.ipynb`. Les variables sont converties en numérique, les variables constantes ou trop vides sont retirées, les données sont imputées selon `IMPUTATION`, puis standardisées par `StandardScaler` avant l’ACP.

### Étape 4 — K-means

`02_kmeans_analyse.ipynb` utilise exactement la même préparation numérique que l’ACP avant la standardisation et K-means. Le notebook calcule notamment inertie et silhouette pour plusieurs valeurs de `k`.

---

## 3. Conventions communes

### Identifiant étudiant

Tous les CSV d’indicateurs utilisent désormais :

```text
SubjectID,<NomDeLaMetrique>
```

Le champ source est :

- `actor` pour Mirabelle ;
- `studentId` pour Nowledgeable ;
- `SubjectID` pour ProgSnap2.

### Valeurs manquantes

Lorsqu’une métrique ne peut pas être calculée pour un étudiant, le script peut omettre cet étudiant du CSV. Lors de la fusion `outer`, cette absence devient une valeur `NaN`. Cette convention distingue une métrique **non observable** d’une métrique réellement égale à zéro.

Quelques indicateurs de couverture écrivent explicitement zéro lorsque l’absence de couverture est une information définie.

### Comparaison du code

Pour les nouveaux indicateurs de changement de code, seules les fins de ligne sont normalisées :

```text
CRLF / CR → LF
```

Les espaces, commentaires et indentations restent significatifs. Ainsi une modification de mise en forme est considérée comme une modification de code, sauf simple différence de fin de ligne.

### Doublons

Quand l’identifiant est disponible :

- Mirabelle : les nouveaux traitements retirent les doublons `_id.$oid` lorsque cela est pertinent ;
- Nowledgeable : les scripts temporels ou par tentative retirent les doublons `answerUuid`.

---

# 4. Indicateurs Mirabelle

Les tests de Mirabelle sont **écrits par les étudiants**. Un taux de réussite ou une réussite complète signifie donc « réussi par rapport à la suite de tests actuellement écrite par l’étudiant », et non « solution certifiée correcte par une suite de tests enseignante exhaustive ».

## 4.1 `SessionCount`

**Script :** `session_count_Mirabelle.py`  
**Champs :** `actor`, `verb`, `timestamp.$date`  
**Événements :** uniquement `verb == "Run.Test"`.

Pour un étudiant, les `Run.Test` sont triés par date. Avec un seuil `g = 5 min` :

\[
SessionCount = 1 + \sum_{i=2}^{n} \mathbf{1}(t_i-t_{i-1}>g)
\]

Une différence exactement égale à 5 minutes reste dans la même session ; il faut un écart **strictement supérieur** au seuil.

## 4.2 `SessionSpanMinutes`

**Script :** `session_span_Mirabelle.py`  
**Champs :** `actor`, `verb`, `timestamp.$date`.

Les `Run.Test` utilisent le même découpage de sessions que `SessionCount` (pause strictement supérieure à 5 minutes). Pour chaque session `s` :

\[
Span_s = \frac{\max(t_s)-\min(t_s)}{60}
\]

puis :

\[
SessionSpanMinutes = mean_s(Span_s)
\]

Une session réduite à un seul `Run.Test` a une durée de 0 minute. Les longues pauses qui ouvrent une nouvelle session ne sont plus incluses dans cette métrique.

## 4.3 `TestPassRate`

**Script :** `test_pass_rate_Mirabelle.py`  
**Champs :** `actor`, `verb`, `tests[].status`, `tests[].verdict`.

Un cas est réussi si `status` représente vrai/1/pass/passed, ou si son `verdict` commence par `Passed`.

\[
TestPassRate = \frac{N_{cas\ réussis}}{N_{cas\ observables}}
\]

Chaque exécution compte : un même test relancé dix fois contribue dix fois au dénominateur.

## 4.4 `FailedTestRunRatio`

**Script :** `failed_run_ratio_Mirabelle.py`  
**Champs :** `actor`, `verb`, `tests[].verdict`.

Un `Run.Test` non vide est marqué « failed » s’il contient au moins un `FailedVerdict`.

\[
FailedTestRunRatio = \frac{N_{Run.Test\ avec\ FailedVerdict}}{N_{Run.Test\ non\ vides}}
\]

## 4.5 `ExceptionTestRunRatio`

**Script :** `exception_run_ratio_Mirabelle.py`  
**Champs :** `actor`, `verb`, `tests[].verdict`.

\[
ExceptionTestRunRatio = \frac{N_{Run.Test\ avec\ ExceptionVerdict}}{N_{Run.Test\ non\ vides}}
\]

Il distingue les runs levant une exception des simples résultats fonctionnellement incorrects.

## 4.6 `FunctionCoverage`

**Script :** `function_coverage_Mirabelle.py`  
**Champs :** `actor`, `tests[].name`, `tests[].tested_line`, `tests[].filename`, `filename_infere`, `tests[].status`, `P_codeState`.

L’identité d’une fonction est :

\[
(fichier, nom\_de\_fonction)
\]

Le nom est extrait prioritairement de `tests[].name`, puis de `tested_line`. Une fonction est considérée comme traitée si :

\[
\max(status)=True
\]

**ou** si au moins deux `P_codeState` distincts ont été observés dans des `Run.Test` où cette fonction apparaît.

Finalement :

\[
FunctionCoverage = N_{fonctions\ traitées}
\]

Cette définition vise à reconnaître un effort de travail même lorsque l’étudiant n’a encore aucun test réussi.

## 4.7 `ErrorQuotient_FE`

**Script :** `eq_FE_Mirabelle.py`  
**Champs :** `actor`, `timestamp.$date`, `filename_infere`, `P_codeState`, `tests[].verdict`.

Les erreurs sont identifiées à une granularité **grossière** : `FailedVerdict` et `ExceptionVerdict`.

Les `Run.Test` sont triés et segmentés par fichier ainsi que par session d’activité (pause > 5 min). Les relances consécutives à code inchangé sont ignorées à l’intérieur d’un même segment.

Pour une paire comparable de tentatives `(e1,e2)` :

\[
s(e_1,e_2)=\frac{8I(E_1\neq\emptyset \land E_2\neq\emptyset)+3I(E_1\cap E_2\neq\emptyset)}{11}
\]

puis :

\[
ErrorQuotient\_FE = \frac{1}{P}\sum_{p=1}^{P}s_p
\]

avec `P` le nombre de paires comparables.

## 4.8 `ErrorQuotient`

**Script :** `eq_Mirabelle.py`.

Même formule que `ErrorQuotient_FE`, mais l’identité de l’erreur est plus fine :

- `ExceptionVerdict` → dernière ligne du détail d’exception, par exemple `ZeroDivisionError: division by zero` ;
- `FailedVerdict` → couple `(valeur attendue, valeur obtenue)`.

Deux erreurs ne sont donc répétées que si leur message détaillé normalisé est identique.

## 4.9 `RED_FE`

**Script :** `red_FE_Mirabelle.py`.

Même segmentation que l’EQ. Une transition est « répétée » si les deux tentatives adjacentes partagent au moins une catégorie grossière d’erreur (`FailedVerdict` ou `ExceptionVerdict`).

Pour une série de `r` transitions répétées consécutives :

\[
contribution(r)=\frac{r^2}{r+1}
\]

Si `D` est le nombre total de transitions observables :

\[
RED\_FE=\frac{\sum_{series}\frac{r^2}{r+1}}{D}
\]

## 4.10 `RED`

**Script :** `red_Mirabelle.py`.

Même formule que `RED_FE`, mais la répétition est définie par le **message détaillé** de l’erreur, comme pour `ErrorQuotient`.

## 4.11 `AttemptsToFirstSuccess`

**Script :** `attempts_to_first_success_Mirabelle.py`  
**Unité :** `(session d’activité 5 min, fichier, fonction)`.

Dans chaque `Run.Test`, les cas sont regroupés par fonction. Une tentative de fonction est réussie si **tous** les cas observables de cette fonction réussissent :

\[
success(a)=I(\forall test\in a,\ status(test)=True)
\]

Pour une unité `u`, le rang de premier succès est :

\[
A_u=\min\{k\ge1\mid success(a_k)=1\}
\]

Les unités jamais réussies sont censurées et ne contribuent pas à la moyenne :

\[
AttemptsToFirstSuccess=\frac{1}{|U_s|}\sum_{u\in U_s}A_u
\]

## 4.12 `TimeToFirstSuccess`

**Script :** `time_to_first_success_Mirabelle.py`  
**Unité :** `(session d’activité 5 min, fichier, fonction)`.

Pour chaque unité qui atteint un succès complet :

\[
T_u=\frac{t_{premier\ succès}-t_{première\ tentative}}{60}
\]

puis :

\[
TimeToFirstSuccess=mean(T_u)
\]

Une réussite à la première tentative donne `0` minute.

## 4.13 `FirstAttemptSuccessRate`

**Script :** `first_attempt_success_rate_Mirabelle.py`  
**Unité :** `(session d’activité 5 min, fichier, fonction)`.

\[
FirstAttemptSuccessRate=\frac{N_{unités\ dont\ la\ première\ tentative\ réussit}}{N_{unités\ observées}}
\]

Contrairement à `AttemptsToFirstSuccess`, les unités jamais réussies restent au dénominateur.

## 4.14 `ProductiveTransitionRate`

**Script :** `productive_transition_rate_Mirabelle.py`  
**Unité de transition :** `(session d’activité 5 min, fichier)`.

`P_codeState` représente l’état du fichier complet. Deux `Run.Test` successifs ne sont comparés que si :

1. le code a changé ;
2. la suite de tests est identique.

L’identité d’un test est basée sur :

\[
(nom\_fonction, tested\_line, expected\_result)
\]

Le taux de réussite du run est :

\[
PassRate_i=\frac{N_{tests\ réussis,i}}{N_{tests,i}}
\]

Une transition comparable est productive si :

\[
PassRate_{i+1}>PassRate_i
\]

et :

\[
ProductiveTransitionRate=\frac{N_{transitions\ productives}}{N_{transitions\ comparables}}
\]

La contrainte de suite de tests identique est essentielle ici : un étudiant peut ajouter volontairement un test difficile, ce qui ferait baisser le taux de réussite sans que son code ait régressé.

## 4.15 `CodeChangeMagnitude`

**Script :** `code_change_magnitude_Mirabelle.py`  
**Code :** `P_codeState`  
**Transitions :** consécutives au sein du même `(session d’activité 5 min, fichier)`.

Les transitions sans changement sont exclues. Pour deux versions `c1` et `c2`, `difflib.SequenceMatcher` retourne :

\[
Similarity=\frac{2M}{|c_1|+|c_2|}
\]

où `M` est le nombre total de caractères appartenant aux blocs appariés.

On définit :

\[
Magnitude=1-Similarity
\]

puis :

\[
CodeChangeMagnitude=mean(Magnitude)
\]

Une valeur proche de 0 correspond à des changements faibles ; une valeur plus forte à des modifications plus importantes.

## 4.16 `UnchangedRerunRatio`

**Script :** `unchanged_rerun_ratio_Mirabelle.py`.

Pour chaque paire consécutive de `Run.Test` ayant deux `P_codeState` exploitables, dans le même `(session d’activité 5 min, fichier)` :

\[
U_i=I(c_i=c_{i+1})
\]

\[
UnchangedRerunRatio=\frac{\sum_i U_i}{N_{transitions\ observables}}
\]

---

# 5. Indicateurs Nowledgeable

Dans Nowledgeable, les tests sont **fixes et écrits par les enseignants**. `answerScore`, `answerIsRight` et les résultats détaillés sont donc comparables d’une tentative à la suivante pour un même exercice.

## 5.1 `SessionCount`

**Script :** `session_count_Nowledgeable.py`  
**Champs :** `studentId`, `answeredAt`, `answerUuid`.

Après déduplication par `answerUuid` et tri chronologique tous exercices confondus :

\[
SessionCount=1+\sum_{i=2}^{n}I(t_i-t_{i-1}>5\ minutes)
\]

`answeredAt` accepte secondes Unix, millisecondes Unix ou date textuelle.

## 5.2 `TestPassRate`

**Script :** `test_pass_rate_Nowledgeable.py`  
**Champs :** `studentId`, `recordedFeedback.tests[].isRight`.

\[
TestPassRate=\frac{N_{cas\ enseignants\ réussis}}{N_{cas\ enseignants\ exécutés}}
\]

Chaque exécution détaillée est comptée ; un étudiant sans test détaillé exploitable est omis.

## 5.3 `TotalTestCount`

**Script :** `total_test_count_Nowledgeable.py`.

\[
TotalTestCount=\sum_{soumissions} |recordedFeedback["tests"]|
\]

Seuls les éléments structurés comme dictionnaires comptent. Les réexécutions du même test sont comptées plusieurs fois. Un étudiant sans test détaillé reçoit `0`.

## 5.4 `ExerciseCoverage`

**Script :** `exercise_coverage_Nowledgeable.py`  
**Champs :** `exerciceId`, `answerScore`, `answerContent`.

Un exercice `e` est traité si :

\[
\max(answerScore_e)>0
\]

**ou** :

\[
N_{versions\ distinctes\ de\ answerContent,e}\ge2
\]

Alors :

\[
ExerciseCoverage=N_{exercices\ traités}
\]

## 5.5 `FunctionCoverage`

**Script :** `function_coverage_Nowledgeable.py`.

Les définitions de fonctions C/C++ sont extraites de `answerContent`. Les fonctions `test_*` sont ignorées, `main` est conservée. L’identité est :

\[
(exerciceId, nom\_fonction)
\]

Une fonction est traitée si une soumission qui la contient a `answerScore > 0`, ou si au moins deux versions distinctes **du corps de cette fonction** sont observées.

\[
FunctionCoverage=N_{fonctions\ traitées}
\]

Le calcul par fragment de fonction évite qu’un changement dans une autre partie du fichier ne fasse artificiellement augmenter cette couverture.

## 5.6 `ScoreProgression`

**Script :** `score_progression_Nowledgeable.py`  
**Champs :** `exerciceId`, `answeredAt`, `answerScore`, `answerUuid`.

Pour chaque exercice ayant au moins deux tentatives valides :

\[
P_e=score_{dernier}-score_{premier}
\]

puis :

\[
ScoreProgression=mean_e(P_e)
\]

Avec des scores dans `[0,1]`, la métrique appartient à `[-1,1]`. Les exercices à une seule tentative sont exclus car aucune progression n’y est observable.

## 5.7 `MaxUnchangedCodeAttempts`

**Script :** `max_unchanged_code_attempts_Nowledgeable.py`.

Dans chaque exercice, on cherche la plus longue série consécutive de `answerContent` identiques. La métrique étudiant est le maximum sur tous ses exercices.

Exemples :

- `A,A,A` → 3 ;
- `A,A,B,B` → 2 ;
- `A,B,C` → 1.

Une valeur de code manquante casse la série.

## 5.8 `ErrorQuotient`

**Script :** `eq_Nowledgeable.py`.

Les diagnostics sont extraits de `recordedFeedback.stderr`, notamment les lignes `error:` et certaines erreurs d’édition de liens. Ils sont normalisés : casse, espaces, nombres, hexadécimaux et contenus entre guillemets sont neutralisés afin de comparer des **types** d’erreurs plutôt que des identifiants propres au code d’un étudiant.

Les tentatives sont segmentées par `exerciceId`. Un feedback absent coupe la séquence et une relance consécutive à `answerContent` identique est ignorée.

Pour chaque paire comparable :

\[
s=\frac{8I(E_1\neq\emptyset\land E_2\neq\emptyset)+3I(E_1\cap E_2\neq\emptyset)}{11}
\]

puis :

\[
ErrorQuotient=mean(s)
\]

## 5.9 `RED`

**Script :** `red_Nowledgeable.py`.

Même préparation et identité d’erreur que l’EQ. Pour chaque série de `r` transitions adjacentes partageant au moins un type d’erreur :

\[
contribution(r)=\frac{r^2}{r+1}
\]

Puis, avec `D` transitions observables :

\[
RED=\frac{\sum contribution(r)}{D}
\]

## 5.10 `AttemptsToFirstSuccess`

**Script :** `attempts_to_first_success_Nowledgeable.py`  
**Unité :** `exerciceId`.

Le succès complet est défini par :

\[
success=I(answerIsRight=True)
\]

Pour un exercice réussi :

\[
A_e=rang\ de\ la\ première\ soumission\ avec\ answerIsRight=True
\]

puis :

\[
AttemptsToFirstSuccess=mean(A_e)
\]

Les exercices jamais entièrement corrects sont exclus de cette moyenne censurée.

## 5.11 `TimeToFirstSuccess`

**Script :** `time_to_first_success_Nowledgeable.py`.

Pour chaque exercice qui atteint un succès complet :

\[
T_e=\frac{answeredAt_{premier\ succès}-answeredAt_{première\ tentative}}{60}
\]

\[
TimeToFirstSuccess=mean(T_e)
\]

C’est du temps calendaire entre soumissions ; une pause hors activité est donc incluse.

## 5.12 `FirstAttemptSuccessRate`

**Script :** `first_attempt_success_rate_Nowledgeable.py`.

\[
FirstAttemptSuccessRate=\frac{N_{exercices\ avec\ première\ réponse\ correcte}}{N_{exercices\ tentés}}
\]

Les exercices jamais réussis restent au dénominateur.

## 5.13 `ProductiveTransitionRate`

**Script :** `productive_transition_rate_Nowledgeable.py`.

Deux soumissions consécutives du même exercice sont comparables si leurs codes sont présents, différents, et si leurs `answerScore` sont exploitables.

Une transition est productive si :

\[
answerScore_{i+1}>answerScore_i
\]

Ainsi :

\[
ProductiveTransitionRate=\frac{N_{changements\ de\ code\ augmentant\ le\ score}}{N_{changements\ de\ code\ comparables}}
\]

`answerScore` est utilisé plutôt que `answerIsRight`, car un passage de 0.25 à 0.75 est une progression réelle même sans réussite complète.

## 5.14 `CodeChangeMagnitude`

**Script :** `code_change_magnitude_Nowledgeable.py`.

Même distance que dans Mirabelle, mais appliquée à `answerContent`, entre soumissions consécutives du même `exerciceId`, en excluant les codes identiques :

\[
Magnitude=1-\frac{2M}{|c_1|+|c_2|}
\]

\[
CodeChangeMagnitude=mean(Magnitude)
\]

## 5.15 `UnchangedRerunRatio`

**Script :** `unchanged_rerun_ratio_Nowledgeable.py`.

Dans chaque exercice :

\[
UnchangedRerunRatio=\frac{N_{paires\ consécutives\ avec\ answerContent_i=answerContent_{i+1}}}{N_{paires\ consécutives\ avec\ deux\ codes\ observables}}
\]

---

# 6. Indicateurs ProgSnap2

## Prétraitement historique commun

Les scripts ProgSnap2 appellent `data_filter.load_main_table()` puis, pour la plupart, `utils.calculate_metric_map()`.

Le comportement historique est conservé :

1. `MainTable.csv` est chargé ;
2. si `SessionID` n’existe pas, `data_filter` en crée ;
3. les sessions avec moins de `MIN_COMPILES = 4` compilations sont supprimées ;
4. les étudiants dont le nombre de sessions conservées a un z-score inférieur à `MIN_SESSIONS_Z = -2` sont supprimés ;
5. la fonction de métrique est calculée **par session** ;
6. la valeur finale de l’étudiant est généralement la **moyenne de ses valeurs de session**.

### Note sur `GAP_TIME`

Le seuil ProgSnap2 est maintenant exprimé sans ambiguïté en **minutes** : `GAP_TIME = 20.0`, soit les `1200` secondes visées par la valeur historique. `assign_session_ids` affecte l’événement situé après une pause à la nouvelle session (et non à l’ancienne). La version du cache a été incrémentée afin d’éviter la réutilisation de sessions calculées avec l’ancienne logique.

## 6.1 `CompileCount`

**Script :** `compile_count.py`.

Pour une session :

\[
C_s=N(EventType="Compile")
\]

Puis :

\[
CompileCount=mean_s(C_s)
\]

Il s’agit donc du **nombre moyen de compilations par session filtrée**, et non du total étudiant.

## 6.2 `CompileSpanMinutes`

**Script :** `compile_span.py`.

Pour chaque session :

\[
Span_s=\frac{\max(ServerTimestamp_{Compile})-\min(ServerTimestamp_{Compile})}{60}
\]

Puis :

\[
CompileSpanMinutes=mean_s(Span_s)
\]

## 6.3 `CompileSuccessRate`

**Script :** `compil_ratio.py`.

Par session :

\[
R_s=\frac{N(Compile.Result="Success")}{N(Success)+N(Error)}
\]

Puis :

\[
CompileSuccessRate=mean_s(R_s)
\]

## 6.4 `MinutesFromGlobalFirstCompile`

**Script :** `first_compile_vs_global_first.py`.

Soit `T0` la première compilation de toute la table filtrée. Pour une session `s` :

\[
D_s=\max\left(0,\frac{t_{first,s}-T_0}{60}\right)
\]

Puis :

\[
MinutesFromGlobalFirstCompile=mean_s(D_s)
\]

## 6.5 `MinutesToGlobalLastCompile`

**Script :** `last_compile_vs_global_last.py`.

Soit `T1` la dernière compilation de toute la table filtrée. Pour une session :

\[
D_s=\max\left(0,\frac{T_1-t_{last,s}}{60}\right)
\]

Puis moyenne par étudiant.

## 6.6 `FracLong`

**Script :** `frac_long.py`.

Dans une session, les compilations sont triées. Pour un seuil `g=5 min` :

\[
FracLong_s=\frac{N(t_i-t_{i-1}>g)}{N_{intervalles}}
\]

Puis :

\[
FracLong=mean_s(FracLong_s)
\]

Les sessions avec moins de deux compilations exploitables ne fournissent pas de valeur.

## 6.7 `SessionCount` — sémantique historique

**Script :** `session_count.py`.

Attention au nom : `data_filter` a déjà créé des `SessionID`. À l’intérieur de **chaque session retenue**, le script recompte des sous-sessions séparées par plus de 5 minutes entre compilations :

\[
SubSessionCount_s=1+\sum I(\Delta t_i>5min)
\]

Puis :

\[
SessionCount=mean_s(SubSessionCount_s)
\]

Ce n’est **pas** le nombre total de sessions de l’étudiant.

## 6.8 `MeanTestScore`

**Script :** `mean_test_score.py`.

Par session, on sélectionne les événements dont `EventType` commence par `Run`. S’il n’y en a aucun, le script se replie sur toutes les lignes possédant un `Score` numérique.

\[
MeanScore_s=mean(Score)
\]

puis :

\[
MeanTestScore=mean_s(MeanScore_s)
\]

## 6.9 `MinutesToScore1`

**Script :** `time_to_score1.py`.

Pour chaque session :

- origine = première compilation ; si aucune, premier événement daté ;
- succès = premier `Run.Program` tel que `Score >= 1 - 10^{-9}` ;
- si aucun succès observable, la valeur est fixée à **60 min**.

\[
T_s=\begin{cases}
(t_{succès}-t_{départ})/60 & \text{si succès}\cr
60 & \text{sinon}
\end{cases}
\]

puis :

\[
MinutesToScore1=mean_s(T_s)
\]

## 6.10 `ErrorQuotient` — script protégé

**Script :** `eq.py` — **non modifié**.

Dans chaque session, les compilations sont triées par `Order`. `utils.extract_compile_pair_indexes` :

- ignore les compilations consécutives de même `CodeStateID` ;
- segmente par `SessionID`, `ProblemID` et `AssignmentID`.

Les erreurs associées à une compilation sont les événements `Compile.Error` dont `ParentEventID` pointe vers l’événement `Compile`.

Pour chaque paire :

\[
s=\frac{8I(E_1\neq\emptyset\land E_2\neq\emptyset)+3I(Type_1\cap Type_2\neq\emptyset)}{11}
\]

`Type` correspond ici à `CompileMessageType`.

L’EQ d’une session est la moyenne des scores de paire et l’EQ étudiant est la moyenne des EQ de session via `utils.calculate_metric_map`.

## 6.11 `RED` — script protégé

**Script :** `red.py` — **non modifié**.

Dans chaque segment, deux compilations consécutives sont considérées comme répétant une erreur si elles partagent au moins un `CompileMessageType`.

Pour toute série de `r` transitions répétées :

\[
contribution(r)=\frac{r^2}{r+1}
\]

Pour une session, la somme est divisée par le nombre total de transitions de ses segments. La valeur étudiant est ensuite la moyenne des sessions calculables.

## 6.12 `WatWin` — script protégé

**Script :** `watwin.py` — **non modifié**.

WatWin combine persistance des erreurs et temps entre compilations.

Le prétraitement calcule, par étudiant, la moyenne `μ` et l’écart-type `σ` des temps entre une compilation erronée et la compilation suivante lorsque le code change.

Pour une paire où la première compilation est en erreur, le score brut peut recevoir :

- `+4` si les données de message (`CompileMessageData`) sont identiques ;
- `+4` si au moins un `CompileMessageType` est commun ;
- `+2` si la ligne source extraite de `SourceLocation` est identique ;
- score temporel : `+1` si `Δt < μ-σ`, `+25` si `Δt > μ+σ`, sinon `+15`.

Le score de session est normalisé selon le code historique par :

\[
WatWin_s=\frac{score/35}{N_{compilations}-1}
\]

puis la chaîne historique agrège les sessions par étudiant.

### Limitation du fichier fourni

Le `MainTable.csv` actuellement fourni **ne contient pas la colonne `SourceLocation`**, alors que `watwin.py` l’utilise. Le pipeline nettoyé détecte cette absence avant exécution et marque WatWin comme `missing_columns` dans `run_report.csv`, au lieu de modifier le script ou de produire un résultat approximatif.

---

# 7. Interprétation des six nouveaux indicateurs communs

Les six indicateurs ajoutés à Mirabelle et Nowledgeable sont volontairement proches conceptuellement, mais leur interprétation n’est pas toujours identique :

| Indicateur | Mirabelle | Nowledgeable |
|---|---|---|
| `AttemptsToFirstSuccess` | premier succès par fonction selon les tests étudiants présents | premier exercice totalement correct selon `answerIsRight` |
| `TimeToFirstSuccess` | durée jusqu’au succès de la fonction dans une session | durée jusqu’au succès complet de l’exercice |
| `FirstAttemptSuccessRate` | réussite de tous les tests étudiants de la fonction dès sa première tentative | exercice correct dès la première soumission |
| `ProductiveTransitionRate` | amélioration du pass-rate seulement à suite de tests identique | augmentation de `answerScore` après changement de code |
| `CodeChangeMagnitude` | distance entre `P_codeState` successifs d’un fichier | distance entre `answerContent` successifs d’un exercice |
| `UnchangedRerunRatio` | relance de `Run.Test` à `P_codeState` identique | nouvelle soumission à `answerContent` identique |

Cette distinction évite d’interpréter les tests étudiants de Mirabelle comme un instrument fixe alors qu’ils font eux-mêmes partie du comportement observé.

---

# 8. Références scientifiques principales

Les métriques historiques EQ, RED et WatWin proviennent de travaux sur l’analyse des erreurs et comportements de compilation de programmeurs novices ; les indicateurs de progression et de trajectoire de développement s’inscrivent dans la littérature plus générale sur les traces de programmation.

- Jadud, M. C. (2006). *Methods and tools for exploring novice compilation behaviour*. ICER. DOI: `10.1145/1151588.1151600`.
- Becker, B. A. et al. (2016). *A New Metric to Quantify Repeated Compiler Errors for Novice Programmers*. SIGCSE. DOI: `10.1145/2899415.2899463`.
- Watson, C., Li, F. W. B., & Godwin, J. L. (2013). *Predicting Performance in an Introductory Programming Course by Logging and Analyzing Student Programming Behavior*. ICALT. DOI: `10.1109/ICALT.2013.99`.
- Edwards, S. H., & Li, Z. (2016). *Towards Progress Indicators for Measuring Student Programming Effort During Solution Development*. Koli Calling. DOI: `10.1145/2999541.2999561`.
- Price, T. W. et al. (2020). *ProgSnap2: A Flexible Format for Programming Process Data*. SIGCSE. DOI: `10.1145/3341525.3387373`.

Les six nouveaux indicateurs (`AttemptsToFirstSuccess`, `TimeToFirstSuccess`, `FirstAttemptSuccessRate`, `ProductiveTransitionRate`, `CodeChangeMagnitude`, `UnchangedRerunRatio`) sont des **opérationnalisations explicites adaptées aux champs disponibles dans ces deux corpus**. Ils ne doivent pas être présentés comme six métriques standard portant nécessairement ces noms dans la littérature ; leur justification est liée aux travaux sur la progression, les séquences d’états, les itérations de programmation et l’effort de développement.

---

# 9. Contrôles de cohérence intégrés

Le pipeline vérifie notamment :

- existence des scripts déclarés dans le registre ;
- existence du fichier d’entrée ;
- présence des colonnes requises lorsque celles-ci sont déclarées ;
- code retour du script ;
- existence du CSV attendu ;
- présence de `SubjectID` dans la sortie ;
- détection des noms de métriques dupliqués lors de l’agrégation ;
- suppression automatique des variables non numériques, constantes ou insuffisamment renseignées avant ACP/K-means.

Le détail de chaque exécution reste disponible dans `csv/<Corpus>/logs/` et `run_report.csv`.

---

# 10. Corrections de cohérence appliquées

Cette version corrige explicitement plusieurs défauts qui pouvaient biaiser ou contaminer les métriques :

- parsing robuste des listes `tests` Mirabelle lorsqu’une apostrophe est doublement échappée ;
- sessions Mirabelle homogénéisées avec un seuil commun de 5 minutes pour les métriques qui segmentent les tentatives ;
- `SessionSpanMinutes` Mirabelle mesure désormais la durée moyenne de ces sessions d’activité ;
- seuil ProgSnap2 corrigé à 20 minutes (`1200` secondes) et affectation correcte du premier événement après une pause ;
- frontières EQ/RED traitées avant l’élimination des relances à code inchangé ;
- validation stricte des CSV produits (`SubjectID`, métrique attendue, unicité, numéricité) ;
- aucune sortie obsolète n’est conservée après un échec lorsque `overwrite=True` ;
- `overwrite=False` réutilise réellement un CSV existant au lieu de le réécrire ;
- l’agrégation refuse désormais les `SubjectID` dupliqués au lieu de garder silencieusement la première ligne ;
- WatWin renvoie un code d’échec lorsque ses colonnes obligatoires sont absentes.

`MinutesToScore1` conserve la pénalité fixe de 60 minutes lorsque le score 1 n’est jamais atteint, car il s’agit d’une convention métrique explicite et non d’un bug d’implémentation.
