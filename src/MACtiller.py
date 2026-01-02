import sys
import subprocess


def read_clipboard():
    """ Read the clipboard using pbpaste and subprocess.
    Returns:
    - str of the content
    - None if there is an error"""

    try:
        # Check if pbpaste is available
        subprocess.run(['which', 'pbpaste'], check=True, capture_output=True, text=True)

        # Use 'pbpaste' to get clipboard content
        process = subprocess.run(
            ['pbpaste'],
            capture_output=True,
            text=True,  # Decode output as text using default encoding
            check=True  # Raise an exception if the command fails
        )
        return process.stdout.strip()
    except Exception as e:
        print(f"An unexpected error occurred while reading clipboard on macOS: {e}", file=sys.stderr)
        return None


def write_clipboard(text: str):
    """ Write the clipboard using pbpaste and subprocess.
    Returns:
    - bool: True if ok, False if there was an error
    """

    try:
        # Check if pbcopy is available
        subprocess.run(['which', 'pbcopy'], check=True, capture_output=True, text=True)

        # Use 'pbcopy' to write to clipboard. Input is piped to stdin.
        process = subprocess.run(
            ['pbcopy'],
            input=text,  # Provide the text as stdin to pbcopy
            text=True,   # Ensure the input is handled as text
            check=True   # Raise an exception if the command fails
        )
        return True
    except Exception as e:
        print(f"An unexpected error occurred while writing to clipboard on macOS: {e}", file=sys.stderr)
        return False

