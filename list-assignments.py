#!/usr/bin/env python3
"""
Displays some selected information from the canvas assignments.
Mainly used for exploring/debugging.
"""

import json

assignments = json.loads(open('.cache/assignments.json').read())

total_files = 0
for a in assignments:
    print(f"---------------------\n{a['name']}---------------\n")
    # Probably the only useful info about the user here is the name.
    # studs = a['f_studs']
    subs = a['f_submissions']
    for sub in subs:
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
        print(sub['student_name'], sub['excused'], sub['attempt'], sub['workflow_state'], sub['grade'], sub['entered_grade'])
        # print(sub['student_name'])# , sub['excused'], sub['attempt'], sub['workflow_state'], sub['grade'], sub['entered_grade'])
        for s in sub['submission_history']:
            print("      ", s['attempt'], s["submitted_at"], s['cached_due_date'])
            for att in s.get('attachments', []):
                # url includes authentication, so can download it easily
                # att.keys: ['content-type', 'created_at', 'display_name',
                # 'filename', 'folder_id', 'hidden',
                # 'hidden_for_user', 'id', 'lock_at', 'locked',
                # 'locked_for_user', 'media_entry_id', 'mime_class',
                # 'modified_at', 'preview_url', 'size',
                # 'thumbnail_url', 'unlock_at', 'updated_at',
                # 'upload_status', 'url', 'uuid']
                print("             ", att['filename'], att['updated_at'], att['size'], att['url'])
                total_files += 1
# print(sorted(list(att.keys())))
print("Total number of files", total_files)
