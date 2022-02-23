#!/usr/bin/env python3
"""
Fuse filesystem for exploring assignments and handins.

Metadata for a given level in a hierarchy is included as .meta files (json format).

Files are downloaded from Canvas when opened in the filesystem. Cached files are stored in CACHE_DIR (default .cache).

Zip files
------
ZipFiles will be automatically mounted as '<pathname>.unp' once they are cached locally. This means that
once you try to read a zip file, it will be available as an unpacked directory locally.

The reason for not providing any 'unzip' directory before downloading the file is that this could cause
accidental download of all zip files if a 'find' or another tool tried to traverse the unzip directories.


TODO
----
- clean up class hierarchy a bit to make the zip files less kludgy.
- safer handling of file types for detecting zip files.
- possibility of using 'touch' or some other method for downloading an assignment without reading the files?
- configurable cache directory.
- rm on a file: remove from cache.
  We may not need to remove zip files that are already mounted from memory even if we remove the file from the cache directory.
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
from fusepy import FUSE, FuseOSError, Operations, LoggingMixIn
import zipfile

CACHE_DIR = ".cache"

DEBUG = False
# LOG_LEVEL = logging.DEBUG
LOG_LEVEL = logging.ERROR


def filter_dict(d, remove_keys):
    """Returns a new dict with all key:values except the ones in remove_keys"""
    return {k : v for k, v in d.items() if k not in remove_keys}


class Entry:
    def __init__(self, pathname, cont, time_entry=None):
        """cont : dict with
        - timestamp in cont[time_entry],
        - necessary for files:
          - id,
          - url
          - size.
        time_entry = entry name in cont for picking up the entry timestamp
        """
        self.cont = cont
        self.pathname = pathname
        p = Path(pathname)
        self.parent = str(p.parent)
        self.fname = str(p.name)
        if (dts := cont.get(time_entry, None)) is not None:
            dt = datetime.datetime.strptime(dts, '%Y-%m-%dT%H:%M:%SZ')
            self.time = dt.timestamp()
        else:
            self.time = cont.get('_time', 0)
        self.size = self.cont.get('size', 0)

    def _cache_path(self, fid):
        return f"{CACHE_DIR}/{fid}"

    def _is_cached(self, cpath):
        return os.path.exists(cpath)

    def get_offline_file(self, fid, url):
        """Reads and returns a cached file, or downloads it and returns it if it isn't in the cache already"""
        cpath = self._cache_path(fid)
        if self._is_cached(cpath):
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

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.pathname}>'


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


class DebugEntry(Entry):
    DEBUG_FILE = "/.debuginfo.json"
    """A debug file that provides json data about the current mounted filesystem"""
    def __init__(self, pathname=None, cont=None, time_entry=None, filter_entries=None):
        d = {}
        super().__init__(self.DEBUG_FILE, d, time_entry=time_entry)
        self._update_str()
        self.time = time()
        self.size = len(self.meta_str)

    def _update_str(self):
        self.meta_str = (json.dumps({'unzipped_files' : ZipEntry.debuglst}, sort_keys=True, indent=4) + "\n").encode('utf-8')

    def read(self, size, offset):
        """Reads a chunk from a file (potentially downloading and cacheing the file if necessary)."""
        start = offset
        end  = offset + size
        return self.meta_str[start:end]


# ###### Zip Files ######################

# TODO: kludgy, but let's figure out how to do this before cleaning it up.

class ZipFileEntry(Entry):
    def __init__(self, path, info, data):
        # A little bit of band-aid. Should modify the hierarchy further up.
        # Need to pick from info object
        dt = datetime.datetime(*info.date_time)
        d = dict(time=dt.strftime('%Y-%m-%dT%H:%M:%SZ'))
        super().__init__(path, d, time_entry='time')
        self._data = data
        self.size = len(data)

    def read(self, size, offset):
        return self._data[offset:offset + size]


class ZipDirEntry(DirEntry):
    def __init__(self, path, info, dtime=None):
        # A little bit of band-aid. Should modify the hierarchy further up.
        if dtime is None:
            # Need to pick from info object
            dt = datetime.datetime(*info.date_time)
        else:
            dt = datetime.datetime.fromtimestamp(dtime)
        d = dict(time=dt.strftime('%Y-%m-%dT%H:%M:%SZ'))
        if path.endswith("/"):
            # Remove trailing slash
            path = path[:-1]
        super().__init__(path, d, time_entry='time')
        logging.log(logging.DEBUG, f"ZipDirEntry {path}")


class ZipEntry(Entry):
    debuglst = []

    def __init__(self, pathname, cont, ctx, time_entry=None):
        super().__init__(pathname, cont, time_entry=time_entry)
        self.is_unpacked = False
        self._data = None
        self.check_unpack(ctx)
        self.ctx = ctx

    def check_unpack(self, ctx):
        if self.is_unpacked:
            return
        fid = self.cont['id']
        url = self.cont['url']
        cpath = self._cache_path(fid)
        if self._is_cached(cpath):
            if self._data is None:
                # It's already cached, so just read it.
                self._data = self.get_offline_file(fid, url)

            try:
                with zipfile.ZipFile(open(cpath, 'rb')) as zf:
                    # Some zipfiles don't include subdirectory entries (only direct paths to files).
                    # This will be handled in add_entry.
                    dir_prefix = self.pathname + ".unp"  # the pathname of the unpack directory
                    # add the root/mount point
                    ctx.add_entry(ZipDirEntry(dir_prefix, None, self.time))
                    # add each of the directories and files listed in the zip file.
                    for info in zf.infolist():
                        path = f"{dir_prefix}/{info.filename}"
                        if info.is_dir():
                            ctx.add_entry(ZipDirEntry(path, info))
                        else:
                            self.debuglst.append(path)
                            ctx.add_entry(ZipFileEntry(path, info, zf.read(info.filename)))
            except zipfile.BadZipFile:
                print(f"Failed to open {self.pathname} ({cpath}) - bad zipfile")

            # b) scan entries and add file and
            # TODO: need a separate directory and file entry type for this as we need to read from the zip file
            # instead of the cache.
            pass

    def read(self, size, offset):
        if self._data is None:
            fid = self.cont['id']
            url = self.cont['url']
            self._data = self.get_offline_file(fid, url)
            self.check_unpack()
        ret = self._data[offset:offset + size]
        return ret


# Some of this class is based on the Context example from the fusepy distribution.
class Context(LoggingMixIn, Operations):
    'Example filesystem to demonstrate fuse_get_context()'
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

    def __init__(self):
        # dirs is used to keep track of files and subdirectories in each directory.
        # files are each file/directory in the filesystem with an Entry object for each file (key = path).
        super().__init__()
        self.dirs = defaultdict(list)
        self.files = {}

    def getattr(self, path, fh=None):
        # uid, gid, pid = fuse_get_context()
        if (entry := self.files.get(path, None)):
            return entry.getattr()
        raise FuseOSError(ENOENT)

    def read(self, path, size, offset, fh):
        # logging.log(logging.DEBUG, f"**read**({path}, {size}, {offset}, {fh})")
        if path in self.files:
            e = self.files[path]
            return e.read(size, offset)
        raise RuntimeError('unexpected path: %r' % path)

    def readdir(self, path, fh):
        # logging.log(logging.DEBUG, f"readdir: {path} {[d.fname for d in dirs.get(path, [])]}")
        return [d.fname for d in self.dirs.get(path, [])]

    def _add_file(self, fn, entry):
        """Adds a file and make sure it's seen in the parent/directory."""
        if fn in self.files:
            print(f"WARNING: {fn} already exists in the file list")
            return
        self.files[fn] = entry
        # Make sure the file is also seen in the parent directory
        self._add_dirent(entry.parent, entry)

    def _add_dirent(self, dpath, entry):
        """Adds an entry to the directory it's contained in.
        Also ensures that there is an entry for the directory in "files".
        """
        if dpath == entry.pathname:
            # TODO: too sleepy now, but it looks like "/" is added for every file or subdirectory of '/', which makes sense.
            # Probably, this should be considered a special case where the root is updated with the timestamp of the most recent
            # of the child nodes.
            if dpath != "/":
                print(f"WARNING: trying to add directory to itself {dpath} {entry}")
                print(self.dirs.get("/"))
                print(self.files.get("/"))
            return
        self.dirs[dpath].append(entry)
        if dpath not in self.files:
            # The parent directory needs a directory entry
            cont = {'_time': entry.time}
            ne = DirEntry(dpath, cont)
            self._add_file(dpath, ne)

    def add_entry(self, entry):
        """Add entry to file/pathnames and directories.
        Will add necessary entries for parent files/directories that lead up to this file if
        they are missing.
        """
        self._add_file(entry.pathname, entry)
        if isinstance(entry, (ZipDirEntry, ZipFileEntry)):
            logging.log(logging.DEBUG, f"add_entry zip file/dir entry for path {entry.pathname} in dir {entry.parent}")


def mount_fs():
    # Make sure the cache directory exists
    os.makedirs(CACHE_DIR, exist_ok=True)

    ctx = Context()

    # The json file contains a list of assignments.
    assignments = json.loads(open(f"{CACHE_DIR}/assignments.json").read())

    # For each level in the hiearchy, a .meta file is added with json encoded metadata for that level in the directory.
    # The information is filtered to avoid replicating everything from a further in at the root level.
    for a in assignments:
        # Top level directory for each assignment.
        a_path = '/' + a['name']
        ctx.add_entry(DirEntry(a_path, a, time_entry='created_at'))
        ctx.add_entry(MetaEntry(a_path, a, time_entry='updated_at', filter_entries={'f_studs', 'f_submissions'}))
        # logging.log(logging.DEBUG, f"{dirs}")
        for sub in a['f_submissions']:
            # Each submission is in a subdirectory with the name of the student.
            sub_path = f"{a_path}/{sub['student_name']}"
            # Students that haven't submitted still show up, but submitted_at is non-existing. This gives us a 0 epoch time.
            ctx.add_entry(DirEntry(sub_path, sub, time_entry='submitted_at'))
            ctx.add_entry(MetaEntry(sub_path, sub, time_entry='submitted_at', filter_entries={'submission_history'}))
            for s in sub['submission_history']:
                # Each version of the submission is listed in a separate subdirectory
                if s['attempt'] is None:
                    # Student hasn't submitted anything.
                    continue
                attempt_path = f"{sub_path}/{s['attempt']}"
                ctx.add_entry(DirEntry(attempt_path, s, time_entry='submitted_at'))
                ctx.add_entry(MetaEntry(attempt_path, s, time_entry='submitted_at'))
                for att in s.get('attachments', []):
                    # Each file in the submission
                    fpath = f"{attempt_path}/{att['filename']}"
                    if fpath.lower().endswith('.zip'):
                        # Note: the 'unp' directory is not added until the zip file is downloaded (by reading it)
                        # The reason for this is to avoid triggering downloads of all zip files using "find", file managers etc.
                        ctx.add_entry(ZipEntry(fpath, att, ctx, time_entry='modified_at'))
                    else:
                        ctx.add_entry(Entry(fpath, att, time_entry='modified_at'))

    ctx.add_entry(DebugEntry())
    print("Ready")

    FUSE(ctx, args.mount, foreground=True, ro=True, allow_other=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--cache')  # cache directory
    parser.add_argument('mount')
    args = parser.parse_args()

    logging.basicConfig(level=LOG_LEVEL)

    if args.cache:
        CACHE_DIR = args.cache

    mount_fs()
