#!/usr/bin/env python3
"""
Downloads information about assignments from the provided course (COURSE_ID).
The information is stored in a json file as data/assignments.json.
"""
# https://github.com/ucfopen/canvasapi/blob/develop/CHANGELOG.md
#    From 0.15 (2019-11-19)
#   CanvasObject.to_json() is now deprecated and will be removed in a future version.
#   To view the original attributes sent by Canvas, enable logs from the requests library.

import canvasapi
import json
import os

BASE_URL  = "https://uit.instructure.com/"   # Canvas for uit.no
COURSE_ID = 16497                            # inf-1400 2020
COURSE_ID = 21176                            # inf-1400 2021

api_key = open("api_key.txt", 'r').readline().strip()
canvas = canvasapi.Canvas(BASE_URL, api_key)
course = canvas.get_course(COURSE_ID)

def stud_to_dict(stud):
    return {
        'id' : stud.id, 
        'display_name' : stud.display_name,
    }

def subm_to_dict(subm, studs):
    return {
        'submitted_at' : subm.submitted_at, 
        'excused' : subm.excused, 
        'attempt' : subm.attempt, 
        'workflow_state' : subm.workflow_state, 
        'grade' : subm.grade, 
        'entered_grade' : subm.entered_grade, 
        'submission_history' : subm.submission_history, 
        'student_name' : studs[subm.user_id]['display_name']
    }

# Make sure the cache directory exists
os.makedirs(".cache", exist_ok=True)
print("Fetching assignments and students")
assignments = list(course.get_assignments())
assignments.sort(key=lambda x: x.name)
alist = []
for a in assignments:
    print('Fetching info for', a.name)
    subs = list(a.get_submissions(include=['submission_history', 'submission_comments']))
    print(' -- got submissions')
    studs = list(a.get_gradeable_students())
    print(' -- got students')
    # ad = json.loads(a.to_json())
    f_studs = {int(s.id) : stud_to_dict(s) for s in studs}
    ad = {
        'created_at' : a.created_at, 
        'updated_at' : a.updated_at,
        'name'  : a.name, 
        'f_studs' : f_studs, 
        'f_submissions' : [subm_to_dict(s, f_studs) for s in subs], 
    }
    alist.append(ad)

with open('.cache/assignments.json', 'w') as f:
    f.write(json.dumps(alist))
