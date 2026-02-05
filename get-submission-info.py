#!/usr/bin/env python3
"""
Downloads information about assignments from the provided course (COURSE_ID).
The information is stored in a json file as data/assignments.json.
"""

import canvasapi
import json
import os
import argparse
import datetime
from config import BASE_URL, COURSE_ID, INCLUDE_COMPLETED, api_key



def stud_to_dict(stud):
    if hasattr(stud, 'display_name'):
        name = stud.display_name
    else:
        # get_users returns users without display_name
        name = stud.short_name

    return {
        'id' : stud.id,
        'display_name' : name,
        'is_completed' : stud.id in students_compl,
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
        'submission_comments' : subm.submission_comments,
        'student_name' : studs[subm.user_id]['display_name'],
        'group' : subm.group,
    }


def has_student_enrollment(enrollments):
    "Any of the enrollments has a student role"
    # Students can have multiple enrollments. Typically at least one for the course and one or more for the groups.
    # Some of the enrollments can be completed if we include that in the query for students. This can be
    # if they are changing groups.
    return any(e['type'] == 'StudentEnrollment' for e in enrollments)


def is_completed_student(user):
    "Has a student enrollment and is not a currently active user"
    # Note that students with a "completed" status in get_users() can still be active as they
    # may simply have switched over to a different group and are therefore registered as completed in the
    # old group. This is why it is necessary to filter out the active users to avoid adding the students twice.
    return has_student_enrollment(user.enrollments) and user.id not in students


def get_compl_submissions(assignment):
    """Submissions from completed students"""
    return [assignment.get_submission(stud_id, include=['submission_history', 'submission_comments', 'group'])
            for stud_id in students_compl]


def store_data(fname, data):
    """Store 'data' as a json file named 'fname'"""
    with open(fname, 'w') as f:
        f.write(json.dumps(data))
    
    
canvas = canvasapi.Canvas(BASE_URL, api_key)

# https://canvasapi.readthedocs.io/en/stable/course-ref.html
course = canvas.get_course(COURSE_ID)


parser = argparse.ArgumentParser()
parser.add_argument("-b", action="store_true", help="Store a backup file with the date in the name")
args = parser.parse_args()

# Make sure the cache directory exists
os.makedirs(".cache", exist_ok=True)

# https://canvasapi.readthedocs.io/en/stable/assignment-ref.html
print("Fetching assignments and students")
assignments = list(course.get_assignments())
assignments.sort(key=lambda x: x.name)

# Active students. {id: canvasapi.user.User, ...}
students = {s.id : s for s in course.get_users(include=['enrollments']) if has_student_enrollment(s.enrollments)}
print(f"  - {len(students)} active students")
# Students that have withddrawn or are marked as concluded/completed/prior, which happens
# to almost all students when the semester is over.
students_compl = {s.id : s for s in course.get_users(enrollment_state=['completed'], include=['enrollments'])
                  if is_completed_student(s)}
print(f"  - {len(students_compl)} completed students sorted by name")
for sid, s in sorted(students_compl.items(), key=lambda kv: kv[1].name):
    print("      - ", s)

alist = []
for a in assignments:
    print('Fetching info for', a.name)
    subs = list(a.get_submissions(include=['submission_history', 'submission_comments', 'group']))
    print(' -- got submissions')
    # NB: this list of students [canvasapi.user.UserDisplay, ...] does not
    # have the same information as students and students_compl
    studs = list(a.get_gradeable_students())
    print(' -- got students')

    if INCLUDE_COMPLETED:
        studs.extend(students_compl.values())
        print(" -- adding submissions from completed students")
        subs += get_compl_submissions(a)

    f_studs = {int(s.id) : stud_to_dict(s) for s in studs}
    ad = {
        'created_at' : a.created_at,
        'updated_at' : a.updated_at,
        'name'  : a.name,
        'f_studs' : f_studs,
        'f_submissions' : [subm_to_dict(s, f_studs) for s in subs],
    }
    alist.append(ad)


store_data('.cache/assignments.json', alist)

if args.b:
    tnow = datetime.datetime.now().strftime("%Y-%m-%d--%H%M")
    bfname = f'.cache/assignments-{tnow}.json'
    print("Storing backup as", bfname)
    store_data(bfname, alist)
    
