def uri_check(uri: str) -> str:
    if ":" not in uri:
        raise ValueError("Invalid URI")
    return uri
