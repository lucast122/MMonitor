import sys

from build_mmonitor_pyinstaller import ROOT
from mmonitor.userside.view import GUI

print(ROOT)
print(f"Before adding folder to sys.path: {sys.path}")

print(f"After adding folder to sys.path: {sys.path}")

def main():
    GUI().start_app()
    # EnhancedView().start_app()


if __name__ == '__main__':
    main()
