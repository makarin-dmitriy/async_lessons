from functools import wraps
import time


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        print(f'Function:{f.__name__}, args:[{args}, {kw}], took: {te - ts:2.4f} sec')
        return result
    return wrap