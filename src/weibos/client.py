#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a wrapper of sinaweibopy3
#           with enhanced error handling.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from weibo3 import APIClient, APIError, _Callable, _Executable
from http.client import BadStatusLine
from urllib.error import URLError, ContentTooShortError
from time import sleep


class UBClient(APIClient):

    def __init__(self, *args, **kwargs):
        super(UBClient, self).__init__(*args, **kwargs)

    def __getattr__(self, attr):
        if "__" in attr:
            return super(UBClient, self).__getattr__(attr)
        return _UBCallable(self, attr)


class _UBCallable(_Callable):

    def __init__(self, *args, **kwargs):
        super(_UBCallable, self).__init__(*args, **kwargs)

    def __getattr__(self, attr):
        if attr == "get":
            return _UBExecutable(self._client, "GET", self._name)
        elif attr == "post":
            return _UBExecutable(self._client, "POST", self._name)
        else:
            name = "%s/%s" % (self._name, attr)
            return _UBCallable(self._client, name)


class _UBExecutable(_Executable):

    # if you find out more, add the error code to the tuple
    UNREASONABLE_ERRORS = (
        10003,  # Remote service error
        10011,  # RPC error
        21321,  # Applications over the unaudited use restrictions
        20007,  # Does multipart has image?
    )

    def __init__(self, *args, **kwargs):
        super(_UBExecutable, self).__init__(*args, **kwargs)

    def __call__(self, **kw):
        error_count = -1

        while 1:
            error_count += 1  # avoid add error_count all the time

            try:
                return super(_UBExecutable, self).__call__(**kw)
            except (BadStatusLine, ContentTooShortError, URLError, OSError, IOError):
                # these are common networking problems:
                # note: OSError/IOError = Bad CRC32 Checksum
                if error_count > 3:
                    sleep(10)
                else:
                    sleep(1)
                continue
            except APIError as e:
                # these are unreasonable API Errors:
                # note: May caused by bugs on Sina's server
                if error_count > 5:
                    raise
                elif e.error_code in self.UNREASONABLE_ERRORS:
                    sleep(1)
                    continue
                else:
                    raise
