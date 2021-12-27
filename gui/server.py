import threading
import subprocess
import pathlib
import webbrowser


class Server(threading.Thread):

    MANAGE = pathlib.Path(__file__).parent.parent.joinpath('manage.py')

    def __init__(self):
        self.stdout = None
        self.stderr = None
        threading.Thread.__init__(self)

    def run(self):
        p = subprocess.Popen(['python', self.MANAGE, 'runserver'],
                             shell=False,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        self.stdout, self.stderr = p.communicate()


def open_dashboard():
    webbrowser.open_new('http://localhost:8000')


def start():
    server = Server()
    server.start()
    threading.Timer(2, open_dashboard).start()
