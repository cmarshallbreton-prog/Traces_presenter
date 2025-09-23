import random
import datetime
data = """{"traces": ["""

student_id = [""""FST_001", "student_name": "Marie Dubois",""", 
              """"FST_002", "student_name": "Jean Dupont",""",
              """"FST_003", "student_name": "Anne Smith",""",
              """"FST_004", "student_name": "Herve Boban",""",
              """"FST_005", "student_name": "Nathalie Aurez",""",
              """"FST_006", "student_name": "Alain Cor","""]

for student in student_id:
    #Lignes de code
    base_value = 0
    trace_time = datetime.datetime.strptime("2025-07-15T09:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(minutes = random.randint(0,10))
    while trace_time < datetime.datetime.strptime("2025-07-15T10:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ"):
        data += """{"student_id":""" + student
        data += """"trace":{
                    "timestamp":"""
        data += "\"" + trace_time.strftime("%Y-%m-%dT%H:%M:%S.%f%Z") + "\","
        trace_time += datetime.timedelta(minutes = random.randint(0,10), seconds = random.randint(1,59))
        data += "\"trace_name\":\"Lignes de code\","
        data += "\"value\":" + str(base_value) + "}}"
        base_value = max(0, base_value + random.randint(-5,20))
        data += ","
    #Warnings
    base_value = 0
    trace_time = datetime.datetime.strptime("2025-07-15T09:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(minutes = random.randint(0,10))
    while trace_time < datetime.datetime.strptime("2025-07-15T10:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ"):
        data += """{"student_id":""" + student
        data += """"trace":{
                    "timestamp":"""
        data += "\"" + trace_time.strftime("%Y-%m-%dT%H:%M:%S.%f%Z") + "\","
        trace_time += datetime.timedelta(minutes = random.randint(5,15), seconds = random.randint(1,59))
        data += "\"trace_name\":\"Warnings\","
        data += "\"value\":" + str(base_value) + "}}"
        base_value = max(0 ,base_value + random.randint(-1,1))
        data += ","
    #Tests
    number_of_tests = 6
    for i in range (1,number_of_tests):
        base_value = False
        trace_time = datetime.datetime.strptime("2025-07-15T09:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(minutes = random.randint(5*i,5*i+5))
        while trace_time < datetime.datetime.strptime("2025-07-15T10:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ"):
            data += """{"student_id":""" + student
            data += """"trace":{
                        "timestamp":"""
            data += "\"" + trace_time.strftime("%Y-%m-%dT%H:%M:%S.%f%Z") + "\","
            data += "\"trace_name\":\"test_" + str(i) + "\","
            if (not base_value):
                data += "\"value\":false}}"
                trace_time += datetime.timedelta(minutes = random.randint(1,5), seconds = random.randint(1,59))
                if (random.randint(1,number_of_tests + 1) > i):
                    base_value = True
            else:
                data += "\"value\":true}}"
                trace_time += datetime.timedelta(minutes = random.randint(5,15), seconds = random.randint(1,59))

            
            data += ","
    #Ouverture fichiers
    base_value = ["Exo_1.py", "Ennonce.pdf", "Exo_2.py", "Exo_3.py"]
    trace_time = datetime.datetime.strptime("2025-07-15T09:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(minutes = random.randint(0,10))
    while trace_time < datetime.datetime.strptime("2025-07-15T10:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ"):
        data += """{"student_id":""" + student
        data += """"trace":{
                    "timestamp":"""
        data += "\"" + trace_time.strftime("%Y-%m-%dT%H:%M:%S.%f%Z") + "\","
        trace_time += datetime.timedelta(minutes = random.randint(5,15), seconds = random.randint(1,59))
        data += "\"trace_name\":\"Ouverture Fichier\","
        data += "\"value\":\"" + random.choice(base_value) + "\"}}"
        data += ","
    #Nom Fonctions fichiers
    base_value = ["ma_fonction", "DiviserParDeux", "aaaaaaa", "mon_autre_fontion"]
    trace_time = datetime.datetime.strptime("2025-07-15T09:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(minutes = random.randint(0,10))
    while trace_time < datetime.datetime.strptime("2025-07-15T10:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ"):
        data += """{"student_id":""" + student
        data += """"trace":{
                    "timestamp":"""
        data += "\"" + trace_time.strftime("%Y-%m-%dT%H:%M:%S.%f%Z") + "\","
        trace_time += datetime.timedelta(minutes = random.randint(5,15), seconds = random.randint(1,59))
        data += "\"trace_name\":\"Nom Fonctions\","
        data += "\"value\":\"" + random.choice(base_value) + "\"}}"
        data += ","
    #Autres actions
    base_value = ["copy_paste", "alt_tab", "firefox_started"]
    trace_time = datetime.datetime.strptime("2025-07-15T09:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(minutes = random.randint(0,10))
    while trace_time < datetime.datetime.strptime("2025-07-15T10:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ"):
        data += """{"student_id":""" + student
        data += """"trace":{
                    "timestamp":"""
        data += "\"" + trace_time.strftime("%Y-%m-%dT%H:%M:%S.%f%Z") + "\","
        trace_time += datetime.timedelta(minutes = random.randint(5,15), seconds = random.randint(1,59))
        data += "\"trace_name\":\"" + random.choice(base_value) + "\"}},"
    
    if student == student_id[-1]:
        data = data[:-1]


data += """],"metadata": {
    "project_name": "Epreuve FST",
    "description": "Simulation d'un examen de programmation pour presentation des indicateurs. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
    "date": "2024-03-15",
    "class": "Math-Info"
  }}"""
with open("data_realistic.json", "a") as f:
    f.write(data)