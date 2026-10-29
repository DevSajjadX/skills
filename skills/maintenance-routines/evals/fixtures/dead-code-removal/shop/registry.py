HANDLERS = {}


def handler(event):
    def wrap(fn):
        HANDLERS[event] = fn
        return fn
    return wrap


def dispatch(event, payload):
    return HANDLERS[event](payload)
