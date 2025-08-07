from caseconverter.flat import flatcase


def flatcase_alias(s: str, **kwargs: object) -> str:
    """Convert a string to flat case with alias handling.

    Example:
        Hello World => helloworld
    """
    return flatcase(s, **kwargs)
