from flask import Flask, redirect, request, render_template, url_for
import webbrowser
import threading
from time import sleep
from colors import color
from waitress import serve
import ctypes

app = Flask(__name__)
drives = None
server = None
closeBrowserThread = None
submitForm:dict = None

@app.route('/')
def index():
    return render_template('index.html', drives=drives)

@app.route('/submit', methods=['POST'])
def submit():
    global submitForm
    submitForm = request.form.to_dict()
    submitForm["exclude-drives"] = request.form.getlist("exclude-drives")

    # close browser soon
    global closeBrowserThread
    closeBrowserThread = threading.Thread(target = closeBrowser, args = ())
    closeBrowserThread.start()
    # return success
    return redirect(url_for('success'))


@app.route('/success')
def success():
    return render_template('success.html')

class ServerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        serve(app, host="localhost", port=3004)  # blocking

    def get_id(self):
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def exit(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), 0)
            print('Exception raise failure')

def openBrowser():
    print('*' * 50)
    print("Launching webservice @ " + color.BOLD + color.BLUE + "http://localhost:3004" + color.END)
    sleep(0.2)
    webbrowser.open("http://localhost:3004", new=2, autoraise=True)   

def closeBrowser():
    sleep(0.2)
    server.exit()


def main(driveList = None):
    global drives
    drives = driveList

    openBrowserThread = threading.Thread(target = openBrowser, args = ())

    global server
    global submitForm
    server = ServerThread()
    openBrowserThread.start()
    server.start()
    server.join()
    openBrowserThread.join()
    closeBrowserThread.join()
    print(color.GREEN + "Recived form data from webform." + color.END)
    print('*' * 50)
    return submitForm

if __name__ == "__main__":
    main()