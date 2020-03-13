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


def smart_hash(obj):
    if isinstance(obj, (str, int)):
        return obj
    return hash(obj)


class LogFormatting:
    fail_string_length = 0
    success_string_length = 0
    result_justify = 0
    input_justify = 0
    max_input_string_len = 50

    def format_input(self, input_data) -> str:
        if len(input_data) > self.max_input_string_len:
            input_data = input_data[:self.max_input_string_len] + '...'
        return input_data

    def update_fail_string_length(self, new_length):
        if new_length > self.fail_string_length:
            self.fail_string_length = new_length

    def update_success_string_length(self, new_length):
        if new_length > self.success_string_length:
            self.success_string_length = new_length

    def update_result_justify(self, new_length):
        if new_length > self.result_justify:
            self.result_justify = new_length

    def update_input_justify(self, new_length):
        if new_length > self.input_justify:
            self.input_justify = new_length


check_mark = '\N{White Heavy Check Mark}'
cache_check_mark = '\N{Large Blue Circle}'
x_mark = '\N{CROSS MARK}'
reload_mark = '\N{Clockwise Rightwards and Leftwards Open Circle Arrows}'


def color_cyan(skk):
    return "\033[96m {}\033[00m".format(skk)


def color_blue(skk):
    return "\033[34m {}\033[00m".format(skk)


def color_green(skk):
    return "\033[92m {}\033[00m".format(skk)


def color_orange(skk):
    return "\033[33m {}\033[00m".format(skk)


def color_red(skk):
    return "\033[91m {}\033[00m".format(skk)
