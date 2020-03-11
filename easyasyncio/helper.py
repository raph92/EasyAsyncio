import hashlib


def hash(obj):
    """
    Since hash() is not guaranteed to give the same result in different
    sessions, we will be using hashlib for more consistent hash_ids
    """
    if isinstance(obj, (set, tuple, list, dict)):
        obj = repr(obj)
    hash_id = hashlib.md5()
    hash_id.update(repr(obj).encode('utf-8'))
    hex_digest = str(hash_id.hexdigest())
    return hex_digest
