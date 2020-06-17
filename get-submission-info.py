#!/usr/bin/env python3
"""
Downloads information about assignments from the provided course (COURSE_ID).
The information is stored in a json file as data/assignments.json.
"""
import canvasapi
import json
import os

BASE_URL  = "https://uit.instructure.com/"   # Canvas for uit.no
COURSE_ID = 16497                            # inf-1400 2020

api_key = open("api_key.txt", 'r').readline().strip()
canvas = canvasapi.Canvas(BASE_URL, api_key)
course = canvas.get_course(COURSE_ID)

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
    ad = json.loads(a.to_json())
    ad['f_studs'] = {int(s.id) : json.loads(s.to_json()) for s in studs}
    ad['f_submissions'] = [json.loads(s.to_json()) for s in subs]
    # Add student names the submissions.
    for s in ad['f_submissions']:
        s['student_name'] = ad['f_studs'][s['user_id']]['display_name']
    alist.append(ad)

with open('.cache/assignments.json', 'w') as f:
    f.write(json.dumps(alist))
