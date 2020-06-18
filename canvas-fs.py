#!/usr/bin/env python
"""
Fuse filesystem for exploring assignments and handins.

Metadata for a given level in a hierarchy is included as .meta files (json format).

Files are downloaded from Canvas when opened in the filesystem. Cached files are stored in .cache.

TODO:
- downloaded zips can be "unpacked". Files and directories inside can be added dynamically.
  One risk with this is if a "find" or similar programs end up triggering downloads of every
  zip file handed in when trying to enter the "unpacked" directories.
- configurable cache directory.
"""

import logging
from errno import ENOENT
from stat import S_IFDIR, S_IFREG
from time import time
from pathlib import Path
from collections import defaultdict
import datetime
import os
import json
import urllib.request
from fusepy import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context


# Make sure the cache directory exists
os.makedirs(".cache", exist_ok=True)


def filter_dict(d, remove_keys):
    """Returns a new dict with all key:values except the ones in remove_keys"""
    return {k : v for k, v in d.items() if k not in remove_keys}


class Entry:
    def __init__(self, pathname, cont, time_entry=None):
        self.pathname = pathname
        self.cont = cont
        p = Path(pathname)
        self.dirname = str(p.parent)
        self.fname = str(p.name)
        self.time = 0
        if (dts := cont.get(time_entry, None)) is not None:
            dt = datetime.datetime.strptime(dts, '%Y-%m-%dT%H:%M:%SZ')
            self.time = dt.timestamp()
        self.size = self.cont.get('size', 0)

    def get_offline_file(self, fid, url):
        """Reads and returns a cached file, or downloads it and returns it if it isn't in the cache already"""
        cpath = f".cache/{fid}"
        if os.path.exists(cpath):
            return open(cpath, 'rb').read()
        r = urllib.request.urlopen(url)
        if r.status == 200:
            data = r.read()
            with open(cpath, 'wb') as f:
                f.write(data)
            return data
        logging.log(logging.DEBUG, f"TODO: check results from reading file {fid} {url} {r.status}")
        raise RuntimeError("Could not get file")

    def read(self, size, offset):
        """Reads a chunk from a file (potentially downloading and cacheing the file if necessary)."""
        start = offset
        end  = offset + size
        fid = self.cont['id']
        url = self.cont['url']
        data = self.get_offline_file(fid, url)
        return data[start:end]

    def getattr(self):
        return dict(st_mode=(S_IFREG | 0o444),
                    st_size=self.size,
                    st_ctime=self.time,
                    st_mtime=self.time,
                    st_atime=self.time)


class DirEntry(Entry):
    def __init__(self, pathname, cont, time_entry=None):
        super().__init__(pathname, cont, time_entry=time_entry)

    def getattr(self):
        return dict(st_mode=(S_IFDIR | 0o555),
                    st_nlink=2,
                    st_ctime=self.time,
                    st_mtime=self.time,
                    st_atime=self.time)


class MetaEntry(Entry):
    """Provide a human readable version of the metadata with prettified .json files added as .meta files in directories."""
    def __init__(self, pathname, cont, time_entry=None, filter_entries=None):
        d = cont if filter_entries is None else filter_dict(cont, filter_entries)
        super().__init__(pathname + "/.meta", d, time_entry=time_entry)
        self.meta_str = (json.dumps(cont, sort_keys=True, indent=4) + "\n").encode('utf-8')
        self.time = time()
        self.size = len(self.meta_str)

    def read(self, size, offset):
        """Reads a chunk from a file (potentially downloading and cacheing the file if necessary)."""
        start = offset
        end  = offset + size
        return self.meta_str[start:end]


def add_entry(entry):
    """Add entry to file/pathnames and directories"""
    files[entry.pathname] = entry
    dirs[entry.dirname].append(entry)


# This is based on the Context example from the fusepy distribution.
class Context(LoggingMixIn, Operations):
    'Example filesystem to demonstrate fuse_get_context()'

    def getattr(self, path, fh=None):
        # uid, gid, pid = fuse_get_context()
        if (entry := files.get(path, None)):
            return entry.getattr()

        if path == "/":
            # TODO: should consider making a "fake" root entry to avoid this type of code.
            dtime = time()
            return dict(st_mode=(S_IFDIR | 0o555),
                        st_nlink=2,
                        st_ctime=dtime,
                        st_mtime=dtime,
                        st_atime=dtime)

        raise FuseOSError(ENOENT)

    def read(self, path, size, offset, fh):
        # logging.log(logging.DEBUG, f"**read**({path}, {size}, {offset}, {fh})")
        if path in files:
            e = files[path]
            return e.read(size, offset)
        raise RuntimeError('unexpected path: %r' % path)

    def readdir(self, path, fh):
        # logging.log(logging.DEBUG, f"readdir: {path} {[d.fname for d in dirs.get(path, [])]}")
        return [d.fname for d in dirs.get(path, [])]

    # Disable unused operations:
    access = None
    flush = None
    getxattr = None
    listxattr = None
    open = None
    opendir = None
    release = None
    releasedir = None
    statfs = None


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('mount')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    assignments = json.loads(open(".cache/assignments.json").read())
    # dirs is used to keep track of files and subdirectories in each directory.
    # files are each file/directory in the filesystem with an Entry object for each file.
    dirs = defaultdict(list)
    files = {}

    # For each level in the hiearchy, a .meta file is added with json encoded metadata for that level in the directory.
    # The information is filtered to avoid replicating everything from a further in at the root level.
    for a in assignments:
        # Top level directory for each assignment.
        subs = a['f_submissions']
        a_path = '/' + a['name']
        add_entry(DirEntry(a_path, a, time_entry='created_at'))
        add_entry(MetaEntry(a_path, a, time_entry='updated_at', filter_entries=['f_studs', 'f_submissions']))
        # logging.log(logging.DEBUG, f"{dirs}")
        for sub in a['f_submissions']:
            # Each submission is in a subdirectory with the name of the student.
            sub_path = f"{a_path}/{sub['student_name']}"
            # Students that haven't submitted still show up, but submitted_at is non-existing. This gives us a 0 epoch time.
            add_entry(DirEntry(sub_path, sub, time_entry='submitted_at'))
            add_entry(MetaEntry(sub_path, sub, time_entry='submitted_at', filter_entries=['submission_history']))
            for s in sub['submission_history']:
                # Each version of the submission is listed in a separate subdirectory
                if s['attempt'] is None:
                    # Student hasn't submitted anything.
                    continue
                attempt_path = f"{sub_path}/{s['attempt']}"
                add_entry(DirEntry(attempt_path, s, time_entry='submitted_at'))
                add_entry(MetaEntry(attempt_path, s, time_entry='submitted_at'))
                for att in s.get('attachments', []):
                    # Each file in the submission
                    add_entry(Entry(f"{attempt_path}/{att['filename']}", att, time_entry='modified_at'))

    fuse = FUSE(
        Context(), args.mount, foreground=True, ro=True, allow_other=True)
