"""
Simple logging system for flight data operations
Keeps logs for the last 24 hours only
"""
import os
from datetime import datetime, timedelta


def get_logger(log_dir="logs"):
    """
    Get a logger that writes to daily log files
    Automatically cleans up logs older than 24 hours

    :param log_dir: Directory to store log files
    :return: logger function
    """
    # Create logs directory if not exists
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Clean up old logs (older than 24 hours)
    cleanup_old_logs(log_dir)

    # Get current log file name (YYYY-MM-DD.log)
    log_filename = datetime.now().strftime("%Y-%m-%d.log")
    log_path = os.path.join(log_dir, log_filename)

    def logger(message, level="INFO"):
        """
        Log a message with timestamp

        :param message: Message to log
        :param level: Log level (INFO, WARNING, ERROR, SUCCESS)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"

        # Print to console
        print(log_line)

        # Write to log file
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception as e:
            print(f"Failed to write to log: {e}")

    return logger


def cleanup_old_logs(log_dir, hours=24):
    """
    Remove log files older than specified hours

    :param log_dir: Directory containing log files
    :param hours: Hours to keep logs (default: 24)
    """
    if not os.path.exists(log_dir):
        return

    cutoff_time = datetime.now() - timedelta(hours=hours)

    for filename in os.listdir(log_dir):
        if not filename.endswith(".log"):
            continue

        filepath = os.path.join(log_dir, filename)

        # Get file modification time
        file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))

        # Delete if older than cutoff
        if file_mtime < cutoff_time:
            try:
                os.remove(filepath)
                print(f"[CLEANUP] Removed old log: {filename}")
            except Exception as e:
                print(f"[ERROR] Failed to remove {filename}: {e}")


# Create a default logger instance
default_logger = get_logger()
