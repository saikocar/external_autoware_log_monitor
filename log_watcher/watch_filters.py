from os.path import isfile, splitext

from watchfiles import Change, DefaultFilter


class UniqueLogFileFilter(DefaultFilter):
    def __init__(self) -> None:
        self.seen_paths: set[str] = set()
        super().__init__()

    def __call__(self, change: Change, path: str) -> bool:
        if path not in self.seen_paths:
            self.seen_paths.add(path)
            return splitext(path)[1] == '.log' and isfile(path) and super().__call__(change, path)
        return False
