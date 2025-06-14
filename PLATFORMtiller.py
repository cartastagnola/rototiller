import sys

# def write_clipboard(text: str):
#     pass

# def read_clipboard():
#     pass

if sys.platform.startswith('linux'):
    from LINUXtiller import *
elif sys.platform == 'win32':
    from WINtiller import *
elif sys.platform == 'darwin':
    from MACtiller import *
else:
    raise (f"Unknown operating system: {sys.platform}")
