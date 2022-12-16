from os import pathsep
from os.path import realpath, dirname, join
import shutil
from os.path import realpath, dirname, join
from subprocess import call

ROOT = dirname(realpath(__file__))


def main():
    entry_point = join(ROOT, 'src', 'mmonitor', '__main__.py')
    placeholder = join(ROOT, 'src', 'resources', 'images', '.placeholder')
    images_dir_dest = join('resources', 'images')
    r_script = join(ROOT, 'src', 'resources', 'r', 'horizon.r')
    r_dir_dest = join('resources', 'r')

    # call(f"pyinstaller -D {entry_point} --name mmonitor --add-data {placeholder}{pathsep}{images_dir_dest} --add-data {r_script}{pathsep}{r_dir_dest}".split()) #use this for building new spec file
    # remove old dist and built for faster rebuilding
    # try:
    #     shutil.rmtree("//home/minion-computer/PycharmProjects/MMonitor/desktop/dist/mmonitor/")
    #     shutil.rmtree("/home/minion-computer/PycharmProjects/MMonitor/desktop/build/mmonitor/")
    # except:
    #     call(f"pyinstaller mmonitor.spec".split())  # use this for using edited spec file
    call(f"pyinstaller mmonitor.spec -y".split())  # use this for using edited spec file


if __name__ == '__main__':
    main()
