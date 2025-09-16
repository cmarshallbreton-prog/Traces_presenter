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
    trace_time = datetime.datetime.strptime("2025-07-15T09:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ")
    while trace_time < datetime.datetime.strptime("2025-07-15T10:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ"):
        data += """{"student_id":""" + student
        data += """"trace":{
                    "timestamp":"""
        data += "\"" + trace_time.strftime("%Y-%m-%dT%H:%M:%S.%f%Z") + "\","
        trace_time += datetime.timedelta(minutes = random.randint(0,10), milliseconds = random.randint(1,59))
        data += "\"trace_name\":\"Lignes de code\","
        data += "\"value\":" + str(base_value) + "}}"
        base_value += random.randint(-5,20)
        if trace_time < datetime.datetime.strptime("2025-07-15T10:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ"):
            data += ","
    #Warnings
    base_value = 0
    trace_time = datetime.datetime.strptime("2025-07-15T09:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ")
    while trace_time < datetime.datetime.strptime("2025-07-15T10:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ"):
        data += """{"student_id":""" + student
        data += """"trace":{
                    "timestamp":"""
        data += "\"" + trace_time.strftime("%Y-%m-%dT%H:%M:%S.%f%Z") + "\","
        trace_time += datetime.timedelta(minutes = random.randint(5,15), milliseconds = random.randint(1,59))
        data += "\"trace_name\":\"Warnings\","
        data += "\"value\":" + str(base_value) + "}}"
        base_value = max(0 ,base_value + random.randint(-1,1))
        if trace_time < datetime.datetime.strptime("2025-07-15T10:00:00.00Z","%Y-%m-%dT%H:%M:%S.%fZ"):
            data += ","

    
    if student != student_id[-1]:
        data += ","


data += """],"metadata": {
    "project_name": "Epreuve FST",
    "description": "Evolution de l'interface utilisateur d'un formulaire pour une banque. Ajout du genre X en plus de M et F.",
    "date": "2024-03-15",
    "class": "Math-Info"
  }}"""
with open("data_realistic.json", "a") as f:
    f.write(data)