"""Seafile API client exceptions."""


class SeafileError(BaseException):
    """Seafile error"""


class SeafileConnectionError(SeafileError):
    """Seafile connection error"""


class SeafileRequestError(SeafileError):
    """Seafile request error"""
