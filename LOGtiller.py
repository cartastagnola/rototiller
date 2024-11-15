import threading
import queue
import time
from enum import Enum


class LoggingLevels(Enum):
    """Logging levels."""
    DEBUG = 1
    INFO = 2
    ERROR = 3


class AsyncLogger:
    def __init__(self, log_file: str, log_level: str):
        self.log_file: str = log_file
        self.queue: queue.Queue = queue.Queue()
        self.log_level: str = log_level


def logging(logger: AsyncLogger, level: str, message: str):
    """Add a log entry to the queue."""
    if LoggingLevels[level].value >= LoggingLevels[logger.log_level].value:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        log_entry = f"{timestamp} - {level} - {message}"
        logger.queue.put(log_entry)


def writeLoggerToFile(logger: AsyncLogger, string: str):
    """Write the queue of the logger to a file."""

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open(logger.log_file, "a") as f:
        f.write("\n\n///////////////////////////////\n")
        f.write(f"NEW SESSION {timestamp}\n")
        f.write("///////////////////////////////\n\n\n")

    while True:
        print("started logger and running")
        if not logger.queue.empty():
            print("queue not empty")
            try:
                log_entry = logger.queue.get(timeout=0.1)  # Process log entries if available
                with open(logger.log_file, "a") as f:
                    f.write(log_entry + "\n")
                logger.queue.task_done()
            except queue.Empty:
                continue  # No log entry, check again until stop event is set
        else:
            print("queue empty")
        time.sleep(1)

def launchLoggerThread(logger: AsyncLogger, string: str):
    loop_thread = threading.Thread(target=writeLoggerToFile, args=(logger, string), daemon=True)
    loop_thread.start()
    return loop_thread
