
import os
import os.path
import errno


def ensure_directory(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno != errno.EEXIST or not os.path.isdir(path):
            raise


class UnrecognizedFormat:
    def __init__(self, prompt):
        self._prompt = prompt

    def __str__(self):
        return self._prompt
