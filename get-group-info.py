#!/usr/bin/env python3

"""
Fetch and print group information.
"""

import canvasapi
import json
import os
import argparse
import datetime
from collections import Counter
import tomllib
from config import BASE_URL, COURSE_ID, INCLUDE_COMPLETED, api_key


canvas = canvasapi.Canvas(BASE_URL, api_key)
course = canvas.get_course(COURSE_ID)

print("Fetching groups")
groups = list(course.get_groups())
print(f" -- got {len(groups)} groups")


num = Counter()
for g in groups:
    s = f"{g.name:20}"
    users = list(g.get_users())
    for u in users:
        s += f" {u.name:35}"
    num[len(users)] += 1
    if len(users) >= 1:
        print(s)

print(num)
