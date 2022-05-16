from os import pathsep
from os.path import realpath, dirname, join
from subprocess import call

ROOT = dirname(realpath(__file__))


def main():
    entry_point = join(root, 'src', 'mmonitor', '__main__.py')
    placeholder = join(root, 'src', 'resources', 'images', '.placeholder')
    images_dir_dest = join('resources', 'images')
    r_script = join(root, 'src', 'resources', 'r', 'horizon.r')
    r_dir_dest = join('resources', 'r')

    call(f"pyinstaller -D {entry_point} --name mmonitor --add-data {placeholder}{pathsep}{images_dir_dest} --add-data {r_script}{pathsep}{r_dir_dest}".split())


if __name__ == '__main__':
    main()
