from PyQt4 import QtCore
from urllib.request import urlretrieve
from urllib.error import URLError, ContentTooShortError
from http.client import BadStatusLine
from WeHack import async
from threading import Event
import os


class SignalSender(QtCore.QObject):

    fetched = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(SignalSender, self).__init__(parent)

    def emit(self, target):
        self.fetched.emit(target)

    def connect(self, target):
        self.fetched.connect(target)

    def disconnect(self, target):
        self.fetched.disconnect(target)


class AsyncFetcher(QtCore.QObject):

    DO_NOT_HAVE = 0
    DOWNLOADED = 1
    DOWNLOADING = 2

    def __init__(self, path, parent=None):
        super(AsyncFetcher, self).__init__(parent)
        self.path = path
        self._signals = {}
        self._modified = Event()

    @staticmethod
    def _formattedFilename(url):
        url_parts = url.split('/')
        return "%s_%s" % (url_parts[-2], url_parts[-1])

    @async
    def _download(self, url, filepath):
        while 1:
            try:
                urlretrieve(url, filepath)
                break
            except (BadStatusLine, ContentTooShortError, URLError):
                continue

        self._modified.wait()
        self._process_callbacks(filepath)

    def _get_state(self, filepath):
        if self._signals.get(filepath, []):
            assert os.path.exists, "The file should exists, but it doesn't exist."
            return self.DOWNLOADING
        elif os.path.exists(filepath):
            return self.DOWNLOADED
        return self.DO_NOT_HAVE

    def _add_callback(self, filepath, callback):
        signal = SignalSender()
        signal.connect(callback)

        try:
            array = self._signals[filepath]
            array.append(signal)
        except KeyError:
            self._signals[filepath] = [signal]

    def _process_callbacks(self, filepath):
        signals = self._signals.get(filepath, [])
        for signal in signals:
            signal.emit(filepath)
            signals.remove(signal)

    def addTask(self, url, callback):
        filename = self._formattedFilename(url)
        filepath = "".join((self.path, filename))

        self._modified.clear()

        state = self._get_state(filepath)
        if state == self.DO_NOT_HAVE:
            self._add_callback(filepath, callback)
            self._download(url, filepath)
        elif state == self.DOWNLOADING:
            self._add_callback(filepath, callback)
            pass
        elif state == self.DOWNLOADED:
            self._modified.set()  # don't let callback delays the event
            callback(filepath)
            return
        else:
            assert False, "Downloaded but downloading now?"

        self._modified.set()