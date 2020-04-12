import functools
import re

import wtypes


class Color(wtypes.String, format="color"):
    ...


class Datetime(wtypes.String, format="date-time"):
    ...


class Time(wtypes.String, format="time"):
    ...


class Date(wtypes.String, format="date"):
    ...


class Email(wtypes.String, format="email"):
    ...


class Idnemail(wtypes.String, format="idn-email"):
    ...


class Hostname(wtypes.String, format="hostname"):
    ...


class Idnhostname(wtypes.String, format="idn-hostname"):
    ...


class Ipv4(wtypes.String, format="ipv4"):
    ...


class Ipv6(wtypes.String, format="ipv6"):
    ...


class Uri(wtypes.String, format="uri"):
    def _httpx_method(self, method, *args, **kwargs):
        return getattr(__import__("httpx"), method)(self, *args, **kwargs)

    get = functools.partialmethod(_httpx_method, "get")
    post = functools.partialmethod(_httpx_method, "post")


class Urireference(wtypes.String, format="uri-reference"):
    ...


class Iri(Uri, format="iri"):
    ...


class Irireference(wtypes.String, format="iri-reference"):
    ...


class Uritemplate(wtypes.String, format="uri-template"):
    def expand(self, **kwargs):
        return __import__("uritemplate").expand(self, kwargs)

    def URITemplate(self):
        return __import__("uritemplate").URITemplate(self)


class Jsonpointer(wtypes.String, format="json-pointer"):
    def resolve_pointer(self, doc, default=None):
        return __import__("jsonpointer").resolve_pointer(doc, self, default=default)


class Relativejsonpointer(wtypes.String, format="relative-json-pointer"):
    ...


class Regex(wtypes.String, format="regex"):
    for k in "compile match finditer findall subn sub split template".split():
        locals()[k] = getattr(re, k)
    del k
