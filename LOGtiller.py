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

    print("starting logger...")
    while True:
        if not logger.queue.empty():
            try:
                while not logger.queue.empty():
                    log_entry = logger.queue.get(timeout=0.1)  # Process log entries if available
                    with open(logger.log_file, "a") as f:
                        f.write(log_entry + "\n")
                    logger.queue.task_done()
            except queue.Empty:
                continue  # No log entry, check again until stop event is set
        else:
            pass
        time.sleep(1)

def rotate_log(file_path):
    # 10 MB in bytes (10 * 1024 * 1024)
    MAX_SIZE = 10 * 1024 * 1024 

    if not os.path.exists(file_path):
        # Create it if it doesn't exist
        open(file_path, 'a').close()
        return

    # Check the size
    if os.path.getsize(file_path) > MAX_SIZE:
        new_path = file_path + ".1"

        # Remove old .log.1 if it already exists to avoid errors
        if os.path.exists(new_path):
            os.remove(new_path)

        # Rename original to .log.1
        os.rename(file_path, new_path)

        # Create a new empty log file
        open(file_path, 'w').close()
        print(f"Log rotated: {file_path} -> {new_path}")
    else:
        print("Log size is within limits.")


def launchLoggerThread(logger: AsyncLogger, string: str):
    loop_thread = threading.Thread(target=writeLoggerToFile, args=(logger, string), daemon=True)
    loop_thread.start()
    return loop_thread
