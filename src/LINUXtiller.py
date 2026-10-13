import os
import shutil
import subprocess
import sys

# Clipboard backends, tried in order. Each entry is (read command, write command).
# The Wayland one is only used when WAYLAND_DISPLAY is set.
_WAYLAND = (['wl-paste', '--no-newline'], ['wl-copy'])
_XCLIP = (['xclip', '-selection', 'clipboard', '-o'], ['xclip', '-selection', 'clipboard', '-i'])
_XSEL = (['xsel', '--clipboard', '--output'], ['xsel', '--clipboard', '--input'])

INSTALL_HINT = "install wl-clipboard (Wayland) or xclip / xsel (X11)"


def _backend():
    """Return the (read, write) commands of the first available clipboard tool,
    or None if there is none."""
    candidates = []
    if os.environ.get('WAYLAND_DISPLAY'):
        candidates.append(_WAYLAND)
    candidates += [_XCLIP, _XSEL]
    for read_cmd, write_cmd in candidates:
        if shutil.which(read_cmd[0]):
            return read_cmd, write_cmd
    return None


def read_clipboard():
    """ Read the clipboard using wl-paste, xclip or xsel.
    Returns:
    - str of the content
    - None if there is an error"""
    backend = _backend()
    if backend is None:
        print(f"No clipboard tool found: {INSTALL_HINT}", file=sys.stderr)
        return None
    try:
        process = subprocess.run(
            backend[0],
            capture_output=True,
            text=True,  # Decode output as text using default encoding
            check=True,  # Raise an exception if the command fails
            timeout=2,
        )
        return process.stdout.strip()
    except Exception as e:
        print(f"An unexpected error occurred while reading the clipboard: {e}", file=sys.stderr)
        return None


def write_clipboard(text: str):
    """ Write the clipboard using wl-copy, xclip or xsel.
    Returns:
    - bool: True if ok, False if there was an error
    """
    backend = _backend()
    if backend is None:
        print(f"No clipboard tool found: {INSTALL_HINT}", file=sys.stderr)
        return False
    try:
        subprocess.run(
            backend[1],
            input=text,  # Provide the text as stdin to the tool
            text=True,   # Ensure the input is handled as text
            check=True,  # Raise an exception if the command fails
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return True
    except Exception as e:
        print(f"An unexpected error occurred while writing to clipboard: {e}", file=sys.stderr)
        return False
