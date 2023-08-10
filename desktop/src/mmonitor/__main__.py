import sys

sys.path.append('/Users/timolucas/PycharmProjects/MMonitor/desktop/')
from mmonitor.userside.view import GUI

from build_mmonitor_pyinstaller import ROOT

print(ROOT)
print(f"Before adding folder to sys.path: {sys.path}")

print(f"After adding folder to sys.path: {sys.path}")

def main():
    GUI().start_app()


if __name__ == '__main__':
    main()
