import importlib

from os import listdir


src = "bot"
extensions = "ext"


def get_extensions():
    """
    Loops through directories and subdirectories to find for cogs that can be
    load into
    """
    base = f'./{src}/{extensions}/'
    path = ''
    for subdirectory in listdir(base):
        path += f'{src}.{extensions}.{subdirectory}.'

        for file in listdir(base+subdirectory):
            if file.startswith("_"):
                continue
            if file.endswith("py"):
                if not file.startswith("IO"):
                    mod = importlib.import_module(path+file[:-3])
                    if getattr(mod, "setup", None) is None:
                        continue
                path += str(file)[:-3]
                yield path
            path = '.'.join(path.split('.')[:-1]) + '.'
        path = ''


EXTENSIONS = frozenset(get_extensions())
