import subprocess
import sys

def read_clipboard():
    """ Read the clipboard using xclip.
    Returns:
    - str of the content
    - None if there is an error"""
    try:
        # Check if xclip is installed
        subprocess.run(['which', 'xclip'], check=True, capture_output=True)

        # Use 'xclip -selection clipboard -o' to get clipboard content
        process = subprocess.run(
            ['xclip', '-selection', 'clipboard', '-o'],
            capture_output=True,
            text=True,  # Decode output as text using default encoding
            check=True  # Raise an exception if the command fails
        )
        return process.stdout.strip()
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return None


def write_clipboard(text: str):
    """ Write the clipboard using xclip.
    Returns:
    - bool: True if ok, False if there was an error
    """

    try:
        # Check if xclip is installed
        subprocess.run(['which', 'xclip'], check=True, capture_output=True, text=True)

        # Use 'xclip -selection clipboard -i' to write to clipboard
        process = subprocess.run(
            ['xclip', '-selection', 'clipboard', '-i'],
            input=text,  # Provide the text as stdin to xclip
            text=True,   # Ensure the input is handled as text
            check=True   # Raise an exception if the command fails
        )
        return True
    except Exception as e:
        print(f"An unexpected error occurred while writing to clipboard: {e}", file=sys.stderr)
        return False
