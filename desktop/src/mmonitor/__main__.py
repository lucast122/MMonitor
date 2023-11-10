import os
import sys

from build_mmonitor_pyinstaller import ROOT
from mmonitor.userside.view import GUI

# set up PYTHONPATH correctly, when running __main__.py

base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_path not in sys.path:
    sys.path.insert(0, base_path)


print(ROOT)
print(f"Before adding folder to sys.path: {sys.path}")

print(f"After adding folder to sys.path: {sys.path}")

def main():
    GUI().start_app()
    # EnhancedView().start_app()


if __name__ == '__main__':
    main()
