from functools import wraps
import time
import asyncio


def timing(f):
    if asyncio.iscoroutinefunction(f):
        @wraps(f)
        async def wrap(*args, **kw):
            ts = time.time()
            result = await f(*args, **kw)
            te = time.time()
            print(f'Function:{f.__name__}, args:[{args}, {kw}], took: {te - ts:2.4f} sec')
            return result
        return wrap
    else:
        @wraps(f)
        def wrap(*args, **kw):
            ts = time.time()
            result = f(*args, **kw)
            te = time.time()
            print(f'Function:{f.__name__}, args:[{args}, {kw}], took: {te - ts:2.4f} sec')
            return result
        return wrap
