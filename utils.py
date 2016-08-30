import re


def pep8case(txt):
    """
        pep8case converts a string using the lower case function

    :param  txt: a string
    :type   txt: ``str``
    :return: a string with underscores and lowercase letters
    :rtype:   ``str``

    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', txt)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()