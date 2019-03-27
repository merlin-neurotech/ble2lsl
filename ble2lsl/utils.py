"""Utilities for use within ble2lsl."""

from warnings import warn


def subdicts_to_attrdicts(dict_):
    for key in dict_:
        try:
            dict_[key].keys()
            dict_[key] = AttrDict(dict_[key])
            dicts_to_attrdicts(dict_[key])
        except AttributeError:
            pass


class AttrDict(dict):
    """Dictionary whose keys can be referenced like attributes."""
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, *args, **kwargs):
        subdicts_to_attrdicts(kwargs)
        super().__init__(*args, **kwargs)


def invert_map(dict_):
    """Invert the keys and values in a dict."""
    inverted = {v: k for k, v in dict_.items()}
    return inverted


def bad_data_size(data, size, data_type="packet"):
    """Return `True` if length of `data` is not `size`."""
    if len(data) != size:
        warn('Wrong size for {}, {} instead of {} bytes'
             .format(data_type, len(data), size))
        return True
    return False


def dict_partial_from_keys(keys):
    """Return a function that constructs a dictionary with predetermined keys.
    """
    def dict_partial(values):
        return dict(zip(keys, values))
    return dict_partial
