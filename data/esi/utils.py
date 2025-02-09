class ESIError(Exception):
    def __init__(self, *args: object, error_code: int | None = None) -> None:
        super().__init__(*args)
        self.error_code = error_code


def cached(func):
    def wrapper(self, *args, **kwargs):
        if self.cache:
            pass

        return func(*args, **kwargs)

    return wrapper
