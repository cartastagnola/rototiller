import sys
import win32clipboard


def read_clipboard():
    """ Read the clipboard using win32clipboard.
    Returns:
    - str of the content
    - None if there is an error"""
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            return text
        else:
            print("Warning (Windows): Clipboard does not contain text data.", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error (Windows) reading clipboard: {e}", file=sys.stderr)
        return None
    finally:
        # Ensure the clipboard is always closed, even if an error occurs
        try:
            win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"Error (Windows) closing clipboard after read attempt: {e}", file=sys.stderr)


def write_clipboard(text: str):
    """ Write the clipboard using win32clipboard.
    Returns:
    - bool: True if ok, False if there was an error
    """
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()  # Clear existing clipboard content
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
        return True
    except Exception as e:
        print(f"Error (Windows) writing to clipboard: {e}", file=sys.stderr)
        return False
    finally:
        # Ensure the clipboard is always closed, even if an error occurs
        try:
            win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"Error (Windows) closing clipboard after write attempt: {e}", file=sys.stderr)

