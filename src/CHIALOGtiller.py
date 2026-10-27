"""Archive of the chia log.

chia keeps only log_maxfilesrotation rotated files (7 of 50 MB by default, a few weeks), so each
rotated file (debug.log.1, debug.log.2, ...) is copied in ARCHIVE_DIR, gzip compressed (about 6x
smaller), and named by the time of its first line: a file that chia renamed (.1 -> .2) has the
same name in the archive, so it is copied once. The current debug.log is archived after chia
rotates it. The archive is plain gzip: zcat, zgrep, zless read it.
"""

import gzip
import os
import re
import shutil
import threading
import time
from pathlib import Path

import src.CONFtiller as CONF
from src.CONFtiller import debug_logger, logging

CHIA_LOG = str(Path(CONF.DEFAULT_ROOT_PATH) / CONF.config.get('logging', {}).get('log_filename', 'log/debug.log'))
CHIA_LOG_PATHS = [CHIA_LOG] + [f"{CHIA_LOG}.{i}" for i in range(1, 21)]  # the newest first
ARCHIVE_DIR = CONF.DB_FOLDER / 'chia_log'
ARCHIVE_EVERY = 3600  # seconds between two checks for new rotated files

LINE_TIME = re.compile(rb'^(\d{4}-\d\d-\d\d)T(\d\d):(\d\d):(\d\d)(?:\.(\d{3}))?')


class ArchiveState:
    """What the archive holds, for the screens; updated by archive_rotated"""
    files = 0
    size = 0  # bytes, compressed
    oldest = None  # name of the oldest archive
    last_run = None
    error = None


def archive_name(path) -> str:
    """debug_2026-10-20T01-09-27.353.log.gz, from the time of the first line; None without it"""
    with open(path, 'rb') as f:
        match = LINE_TIME.match(f.readline())
    if match is None:
        return None
    day, h, m, s, ms = match.groups()
    return f"debug_{day.decode()}T{h.decode()}-{m.decode()}-{s.decode()}.{(ms or b'000').decode()}.log.gz"


def update_state(folder=ARCHIVE_DIR):
    files = sorted(Path(folder).glob('debug_*.log.gz')) if Path(folder).exists() else []
    ArchiveState.files = len(files)
    ArchiveState.size = sum(f.stat().st_size for f in files)
    ArchiveState.oldest = files[0].name if files else None


def archive_rotated(paths=CHIA_LOG_PATHS, folder=ARCHIVE_DIR):
    """Copy the rotated log files that are not in the archive yet; return the new archives"""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    new = []
    for path in paths[1:]:
        if not os.path.exists(path):
            continue
        name = archive_name(path)
        if name is None or (folder / name).exists():
            continue
        dest = folder / name
        part = folder / (name + '.part')
        with open(path, 'rb') as src, gzip.open(part, 'wb', compresslevel=6) as out:
            shutil.copyfileobj(src, out, 1 << 20)
            stat = os.fstat(src.fileno())  # chia can rename the file meanwhile
        os.utime(part, (stat.st_atime, stat.st_mtime))
        os.replace(part, dest)
        new.append(dest)
        logging(debug_logger, "DEBUG", f"chia log archive: {path} -> {dest}")
    update_state(folder)
    ArchiveState.last_run = time.time()
    return new


def archive_loop():
    while True:
        try:
            archive_rotated()
            ArchiveState.error = None
        except Exception as e:
            ArchiveState.error = str(e)
            logging(debug_logger, "ERROR", f"chia log archive: {e}")
        time.sleep(ARCHIVE_EVERY)


def start_archive_thread():
    thread = threading.Thread(target=archive_loop, daemon=True)
    thread.setName("chia log archive")
    thread.start()
    return thread
