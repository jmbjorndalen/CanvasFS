#!/usr/bin/env python3
"""
Displays some selected information from the canvas assignments.
Mainly used for exploring/debugging.
"""

import json

assignments = json.loads(open('.cache/assignments.json').read())


def newest_update(subinfo):
    """Recursively searches subinfo for 'updated_at' or 'submitted_at' and returns the most recent date"""
    def get_date(d, key):
        v = d.get(key, '')
        if v is None:
            v = ''
        # if v != '':
        #    print("GOT ", key, v)
        return v

    def get_seq(sub):
        if isinstance(sub, list):
            return sub
        if isinstance(sub, dict):
            return sub.values()
        return []
    cur = ''
    if isinstance(subinfo, dict):
        # cur = max('', get_date(subinfo, 'submitted_at'), get_date(subinfo, 'updated_at'))
        cur = max('', get_date(subinfo, 'submitted_at'))
    for c in get_seq(subinfo):
        cur = max(cur, newest_update(c))

    return cur


def sort_str(sub):
    """latest submission date + student name"""
    name = sub.get('student_name', '0zzzzz')
    tm = newest_update(sub)
    if tm == '':
        tm = '0'
    # print(name, tm)
    return tm + name


def get_similarities(sub):
    # each submission has a 'submission_history' list of sub-submissions.
    # each sub-submission has a 'turnitin_data' with 'attachment_x' as keys,
    # and 'attachment_id' : x as id for the attachment, and 'similiarity_score' : (null or some float)
    # as a score. Need to flatten this to a dict of 'id/x' : score
    scores = {}
    # print('SUB', sub)
    for subsub in sub['submission_history']:
        # print('SUBSUB', subsub)
        for td in subsub.get('turnitin_data', {}).values():
            if not isinstance(td, dict):
                # some might have extra info here. Skip that.
                continue
            # print('......', td)
            scores[td['attachment_id']] = td['similarity_score']
    return scores


def attr(att, key):
    return f"{key}={att.get(key, '_NA_')}"


total_files = 0
for a in assignments:
    print(f"---------------------\n{a['name']}---------------\n")
    # Probably the only useful info about the user here is the name.
    # studs = a['f_studs']
    subs = a['f_submissions']
    for sub in sorted(subs, key=sort_str):
        # sub.keys: ['assignment_id', 'attempt', 'body',
        # 'cached_due_date', 'course_id', 'display_name',
        # 'entered_grade', 'entered_score', 'excused',
        # 'extra_attempts', 'grade',
        # 'grade_matches_current_submission', 'graded_at',
        # 'grader_id', 'grading_period_id', 'id', 'late',
        # 'late_policy_status', 'missing', 'points_deducted',
        # 'posted_at', 'preview_url', 'score', 'seconds_late',
        # 'submission_comments', 'submission_history',
        # 'submission_type', 'submitted_at', 'url', 'user_id',
        # 'workflow_state']
        # also: added student_name in the get-submission-info file
        turnitin_scores = get_similarities(sub)
        max_score = max([0] + [v for v in turnitin_scores.values() if type(v) == float])
        print(sub['student_name'], newest_update(sub), sub['excused'], sub['attempt'], sub['workflow_state'], sub['grade'], sub['entered_grade'], f"{max_score=}")
        # print(sub['student_name'])# , sub['excused'], sub['attempt'], sub['workflow_state'], sub['grade'], sub['entered_grade'])
        for s in sub['submission_history']:
            print("      ", s['attempt'], s["submitted_at"], s['cached_due_date'])
            for att in s.get('attachments', []):
                score = turnitin_scores[att.get('id', None)]
                # url includes authentication, so can download it easily
                # att.keys: ['content-type', 'created_at', 'display_name',
                # 'filename', 'folder_id', 'hidden',
                # 'hidden_for_user', 'id', 'lock_at', 'locked',
                # 'locked_for_user', 'media_entry_id', 'mime_class',
                # 'modified_at', 'preview_url', 'size',
                # 'thumbnail_url', 'unlock_at', 'updated_at',
                # 'upload_status', 'url', 'uuid']
                print("             ", attr(att, 'filename'), attr(att, 'updated_at'), attr(att, 'size'),
                      f"{score=}", attr(att, 'url'))
                total_files += 1
        print()
# print(sorted(list(att.keys())))
print("Total number of files", total_files)
