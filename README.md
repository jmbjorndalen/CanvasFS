CanvasFS
=========

This is currently a toy project to experiment with mounting
assignments from Canvas as a file system. The main idea is that it
lets files students hand in and the state of the assignments without
having to download them with a browser. 

To get an idea why: the students in the current course I'm teaching
have handed in 994 files so far. About half of them zip files with
source code.

The file system exposes the revision history for handed in assignments to
make it easier to focus on improvements the students have made.

Currently, it only focuses on assignments. 

Some of the code here might be merged with the
[https://github.com/edvardpedersen/canvashelper](https://github.com/edvardpedersen/canvashelper)
project.


Requirements
------------

It has only been tested with Linux, but fusepy should work with Mac as
well. On Windows, it may work with WSL2 which now has support for Fuse
filesystems.

- Python 3.8+  (sorry, I just had to play with the Walrus operator)
- fusepy : [https://github.com/fusepy/fusepy](https://github.com/fusepy/fusepy)
- canvasapi : [https://github.com/ucfopen/canvasapi](https://github.com/ucfopen/canvasapi)


Setting up
----------

You need an API key for Canvas. The easiest way to do this is to go to
Account/Settings in Canvas. There you can create a new access token.

The token should be stored in `api_key.txt`. This file is not included. 

To fetch information for a given course, edit
`get-submission-info.py`. `BASE_URL` points the the URL for your
canvas installation, while `COURSE_ID` is the numeric id of the course
you want to browse.


Using
------ 

Fetching the metadata from canvas takes a while. To make it easier to
experiment, the metadata is downloaded as follows:

```
python3 get-submission-info.py
```

The data is stored in the `.cache` subdirectory. 

Mounting the filesystem is as simple as: 

```
python3 canvasfs.py tmp
```

Where `tmp` is the directory where you want to mount the assignments. 

Metadata for directories and the files inside the directories is
available as a json file called `.meta`.

Files that students have handed in can be read in the file system
normally. To avoid bothering Canvas too much, the files are cached in
the .cache directory.


### Example: using ls to find the newest hand-ins: 

```
ls -ltr t/Assignment\ 1\ -\ Breakout/
```


Future
-----

Caching downloaded information will probably be removed (or made
optional) in the future to avoid storing too much data on the
computer. If you want to be on the safe side, you can remove the
`.cache` when unmounting. 









