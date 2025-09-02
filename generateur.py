import random
data = """{"traces": ["""

student_id = [""""FST_001", "student_name": "Marie Dubois",""", 
              """"FST_002", "student_name": "Jean Dupont",""",
              """"FST_003", "student_name": "Anne Smith",""",
              """"FST_004", "student_name": "Herve Boban",""",
              """"FST_005", "student_name": "Nathalie Aurez",""",
              """"FST_006", "student_name": "Alain Cor","""]

limit = 1000
for i in range (0,limit):
    data += """{"student_id":""" + random.choice(student_id)
    data += """"trace":{
                    "timestamp":"""
    data += "\"2025-07-15T09:" + str(random.randint(30,59)) + ":" + str(random.randint(10,59)) + "Z\"," 
     
    rdm = random.randint(1,100)
    if rdm in range(1,31):
        data += """"trace_name": "lignes de code",
        "value": """ + str(random.randint(15,100)) + """,
        \"category":["Static"]}"""
    elif rdm in range(31,41):
        data += """"trace_name": "Nom des fonctions",
        "value": \"""" + random.choice(["do_things", "open_door", "drink_coffee", "say_hi"]) + """\",
        \"category":["Static"]}"""
    elif rdm in range(41,71):
        data += """"trace_name": "test_""" + str(random.randint(1,5)) + """",
        "value": """ + random.choice(["true","false"]) + """,
        \"category":["Dynamic"]}"""
    elif rdm in range(71,81):
        data += """"trace_name": "warnings",
        "value": """ + str(random.randint(0,10)) + """,
        \"category":["Dynamic"]}"""
    elif rdm in range(81,91):
        data += """"trace_name": "_""" + random.choice(["copy_paste","window_change", "code_chunk"]) + """\",
        \"category":["Suspicious"]}"""
    elif rdm in range(91,101):
        data += """"trace_name": "&""" + random.choice(["aaa","bbb", "ccc"]) + """\",
        \"category":[]}"""

    data += "}"
    if i != limit-1:
        data += ","

data += """],"metadata": {
    "project_name": "Epreuve FST",
    "description": "Evolution de l'interface utilisateur d'un formulaire pour une banque. Ajout du genre X en plus de M et F.",
    "date": "2024-03-15",
    "class": "Math-Info"
  }}"""








with open("data.json", "a") as f:
    f.write(data)