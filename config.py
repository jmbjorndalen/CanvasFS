#!/usr/bin/env python3

"""Work-in progress to move config settings to a config file (toml).
"""

import tomllib

config = tomllib.loads(open("config.toml", 'r', encoding="utf-8").read())

BASE_URL  = config['base_url']
COURSE_ID = config['course_id']

# To view submissions after a course is closed, or to view students that have withdrawn from the course.
INCLUDE_COMPLETED = config.get('include_completed', True)

api_key = config['api_key']

