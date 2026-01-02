import sys

# def write_clipboard(text: str):
#     pass

# def read_clipboard():
#     pass

if sys.platform.startswith('linux'):
    from src.LINUXtiller import *
elif sys.platform == 'win32':
    from src.WINtiller import *
elif sys.platform == 'darwin':
    from src.MACtiller import *
else:
    raise (f"Unknown operating system: {sys.platform}")
