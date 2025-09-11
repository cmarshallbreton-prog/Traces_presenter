import random
import json
from datetime import datetime, timedelta

# Configuration des étudiants
students = [
    {"id": "FST_001", "name": "Marie Dubois"},
    {"id": "FST_002", "name": "Jean Dupont"},
    {"id": "FST_003", "name": "Anne Smith"},
    {"id": "FST_004", "name": "Herve Boban"},
    {"id": "FST_005", "name": "Nathalie Aurez"},
    {"id": "FST_006", "name": "Alain Cor"}
]

# État initial pour chaque étudiant
student_states = {}
for student in students:
    student_states[student["id"]] = {
        "lines_of_code": random.randint(10, 25),  # Démarrage avec peu de lignes
        "warnings": random.randint(0, 3),         # Peu de warnings au début
        "tests_passed": {},                       # Quels tests ont déjà passé
        "functions_used": [],                     # Fonctions déjà utilisées
        "suspicious_count": 0                     # Compteur d'activités suspectes
    }

# Liste des fonctions disponibles
available_functions = ["do_things", "open_door", "drink_coffee", "say_hi", "calculate", "validate", "process"]
test_names = [f"test_{i}" for i in range(1, 6)]
suspicious_activities = ["copy_paste", "window_change", "code_chunk"]
suspicious_codes = ["aaa", "bbb", "ccc"]

def generate_timestamp(base_time, minutes_offset):
    """Génère un timestamp cohérent basé sur l'offset"""
    new_time = base_time + timedelta(minutes=minutes_offset)
    return new_time.strftime("%Y-%m-%dT%H:%M:%SZ")

def evolve_lines_of_code(current_lines):
    """Fait évoluer le nombre de lignes de code de manière réaliste"""
    # Généralement augmente, parfois stagne, rarement diminue légèrement
    change = random.choices(
        [0, 1, 2, 3, 4, 5, -1],  # Changements possibles
        weights=[10, 20, 25, 20, 15, 5, 5]  # Probabilités
    )[0]
    return max(current_lines + change, 0)

def evolve_warnings(current_warnings, lines_of_code):
    """Fait évoluer le nombre de warnings en fonction du code"""
    # Plus de code = potentiellement plus de warnings, mais tend à diminuer avec le temps
    if lines_of_code < 30:
        # Début : warnings peuvent augmenter
        change = random.choices([-1, 0, 1, 2], weights=[20, 40, 30, 10])[0]
    else:
        # Plus tard : warnings tendent à diminuer (code nettoyé)
        change = random.choices([-2, -1, 0, 1], weights=[25, 35, 30, 10])[0]
    
    return max(current_warnings + change, 0)

def check_test_status(student_id, test_name):
    """Vérifie le statut d'un test (une fois passé, reste passé)"""
    if test_name in student_states[student_id]["tests_passed"]:
        return True
    else:
        # Probabilité de passer le test augmente avec le temps
        if random.random() < 0.15:  # 15% de chance de passer un nouveau test
            student_states[student_id]["tests_passed"][test_name] = True
            return True
        return False

def select_function(student_id):
    """Sélectionne une fonction (tend à réutiliser les fonctions connues)"""
    used_functions = student_states[student_id]["functions_used"]
    
    if used_functions and random.random() < 0.7:  # 70% de chance de réutiliser
        return random.choice(used_functions)
    else:
        # Nouvelle fonction
        new_function = random.choice(available_functions)
        if new_function not in used_functions:
            student_states[student_id]["functions_used"].append(new_function)
        return new_function

# Génération des données
traces = []
base_time = datetime(2025, 7, 15, 9, 30, 0)
limit = 1000

for i in range(limit):
    # Sélection aléatoire d'un étudiant
    student = random.choice(students)
    student_id = student["id"]
    
    # Timestamp progressif
    timestamp = generate_timestamp(base_time, i // 10)  # Une trace toutes les 6 secondes environ
    
    # Sélection du type de trace avec des probabilités réalistes
    trace_type = random.choices(
        ["lines_code", "function_name", "test", "warnings", "suspicious", "empty"],
        weights=[30, 10, 30, 15, 10, 5]
    )[0]
    
    trace = {
        "student_id": student_id,
        "student_name": student["name"],
        "trace": {
            "timestamp": timestamp
        }
    }
    
    if trace_type == "lines_code":
        # Évolution cohérente des lignes de code
        student_states[student_id]["lines_of_code"] = evolve_lines_of_code(
            student_states[student_id]["lines_of_code"]
        )
        trace["trace"].update({
            "trace_name": "lignes de code",
            "value": student_states[student_id]["lines_of_code"],
            "category": ["Static"]
        })
        
    elif trace_type == "function_name":
        # Sélection cohérente des fonctions
        func_name = select_function(student_id)
        trace["trace"].update({
            "trace_name": "Nom des fonctions",
            "value": func_name,
            "category": ["Static"]
        })
        
    elif trace_type == "test":
        # Tests cohérents (une fois passés, restent passés)
        test_name = random.choice(test_names)
        test_result = check_test_status(student_id, test_name)
        trace["trace"].update({
            "trace_name": test_name,
            "value": test_result,
            "category": ["Dynamic"]
        })
        
    elif trace_type == "warnings":
        # Évolution cohérente des warnings
        student_states[student_id]["warnings"] = evolve_warnings(
            student_states[student_id]["warnings"],
            student_states[student_id]["lines_of_code"]
        )
        trace["trace"].update({
            "trace_name": "warnings",
            "value": student_states[student_id]["warnings"],
            "category": ["Dynamic"]
        })
        
    elif trace_type == "suspicious":
        # Activités suspectes (limitées par étudiant)
        if student_states[student_id]["suspicious_count"] < 5:  # Max 5 activités suspectes par étudiant
            activity = random.choice(suspicious_activities)
            student_states[student_id]["suspicious_count"] += 1
            trace["trace"].update({
                "trace_name": f"_{activity}",
                "value": "",
                "category": ["Suspicious"]
            })
        else:
            continue  # Skip cette trace si trop d'activités suspectes
            
    elif trace_type == "empty":
        # Traces vides occasionnelles
        code = random.choice(suspicious_codes)
        trace["trace"].update({
            "trace_name": f"&{code}",
            "value": "",
            "category": []
        })
    
    traces.append(trace)

# Construction du JSON final
data = {
    "traces": traces,
    "metadata": {
        "project_name": "Epreuve FST",
        "description": "Evolution de l'interface utilisateur d'un formulaire pour une banque. Ajout du genre X en plus de M et F.",
        "date": "2024-03-15",
        "class": "Math-Info",
        "generation_info": {
            "total_traces": len(traces),
            "students": len(students),
            "time_span": "2025-07-15T09:30:00Z to 2025-07-15T11:10:00Z"
        }
    }
}

# Sauvegarde
with open("data_coherent.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Fichier généré avec {len(traces)} traces cohérentes")
print("État final des étudiants :")
for student_id, state in student_states.items():
    print(f"  {student_id}: {state['lines_of_code']} lignes, {state['warnings']} warnings, "
          f"{len(state['tests_passed'])} tests passés")