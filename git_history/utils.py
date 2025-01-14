import re

RESERVED = ("_id", "_item", "_version", "_commit", "rowid")
reserved_with_suffix_re = re.compile("^({})_*$".format("|".join(RESERVED)))


def fix_reserved_columns(item):
    if not any(reserved_with_suffix_re.match(key) for key in item):
        return item

    return {_fix_key(key): item[key] for key in item}


def _fix_key(key):
    # Add a trailing _ if it's reserved or reserved with _ suffix
    if reserved_with_suffix_re.match(key):
        return key + "_"
    else:
        return key
