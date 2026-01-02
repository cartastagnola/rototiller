import threading
import queue
import time
from pathlib import Path
from enum import Enum


class LoggingLevels(Enum):
    """Logging levels."""
    DEBUG = 1
    INFO = 2
    ERROR = 3


class AsyncLogger:
    def __init__(self, file_name: str, folder_path: str, log_level: str, log_file_max_size: int, file_count: int = 2):
        self.file_name: str = file_name
        self.folder_path: Path = Path(folder_path)
        self.folder_path.mkdir(parents=True, exist_ok=True)
        self.file_path = self.folder_path / self.file_name
        self.max_file_size = log_file_max_size
        self.queue: queue.Queue = queue.Queue()
        self.log_level: str = log_level
        self.file_count = file_count


def logging(logger: AsyncLogger, level: str, message: str):
    """Add a log entry to the queue."""
    if LoggingLevels[level].value >= LoggingLevels[logger.log_level].value:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_entry = f"{timestamp} - {level} - {message}"
        logger.queue.put(log_entry)


def writeLoggerToFile(logger: AsyncLogger, string: str):
    """Write the queue of the logger to a file."""

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open(logger.file_path, "a") as f:
        f.write("\n\n///////////////////////////////\n")
        f.write(f"NEW SESSION {timestamp}\n")
        f.write("///////////////////////////////\n\n\n")

    print("starting logger...")
    while True:
        if not logger.queue.empty():
            try:
                while not logger.queue.empty():
                    log_entry = logger.queue.get(timeout=0.1)  # Process log entries if available
                    with open(logger.file_path, "a") as f:
                        f.write(log_entry + "\n")
                    logger.queue.task_done()
            except queue.Empty:
                continue  # No log entry, check again until stop event is set
        else:
            pass
        rotate_log(logger)
        time.sleep(1)


def rotate_log(logger: AsyncLogger):

    if not logger.file_path.exists() or logger.file_path.stat().st_size <= logger.max_file_size:
        return

    # shift logs from the last to the first
    for i in range(logger.file_count - 1, 0, -1):
        source = logger.file_path.with_name(f"{logger.file_path.name}.{i}")
        dest = logger.file_path.with_name(f"{logger.file_path.name}.{i + 1}")

        if source.exists():
            if dest.exists():
                dest.unlink()  # delete
            source.rename(dest)

    # Rename the current log to .1
    first_rotated = logger.file_path.with_name(f"{logger.file_path.name}.1")
    if first_rotated.exists():
        first_rotated.unlink()

    logger.file_path.rename(first_rotated)
    logger.file_path.touch()


def launchLoggerThread(logger: AsyncLogger, string: str):
    loop_thread = threading.Thread(target=writeLoggerToFile, args=(logger, string), daemon=True)
    loop_thread.start()
    return loop_thread
