import hashlib


def hash(obj):
    """
    Since hash() is not guaranteed to give the same result in different
    sessions, we will be using hashlib for more consistent hash_ids
    """
    hash_id = hashlib.md5()
    hash_id.update(repr(obj).encode('utf-8'))
    return str(hash_id.hexdigest())
