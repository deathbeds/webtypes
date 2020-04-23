import functools
import re

import wtypes


class Color(wtypes.base.String, format="color"):
    ...


class Datetime(wtypes.base.String, format="date-time"):
    ...


class Time(wtypes.base.String, format="time"):
    ...


class Date(wtypes.base.String, format="date"):
    ...


class Email(wtypes.base.String, format="email"):
    ...


class Idnemail(wtypes.base.String, format="idn-email"):
    ...


class Hostname(wtypes.base.String, format="hostname"):
    ...


class Idnhostname(wtypes.base.String, format="idn-hostname"):
    ...


class Ipv4(wtypes.base.String, format="ipv4"):
    ...


class Ipv6(wtypes.base.String, format="ipv6"):
    ...


class Uri(wtypes.base.String, format="uri"):
    def _httpx_method(self, method, *args, **kwargs):
        return getattr(__import__("httpx"), method)(self, *args, **kwargs)

    get = functools.partialmethod(_httpx_method, "get")
    post = functools.partialmethod(_httpx_method, "post")


class Urireference(wtypes.base.String, format="uri-reference"):
    ...


class Iri(Uri, format="iri"):
    ...


class Irireference(wtypes.base.String, format="iri-reference"):
    ...


class Uritemplate(wtypes.base.String, format="uri-template"):
    def expand(self, **kwargs):
        return __import__("uritemplate").expand(self, kwargs)

    def URITemplate(self):
        return __import__("uritemplate").URITemplate(self)


class Jsonpointer(wtypes.base.String, format="json-pointer"):
    def resolve_pointer(self, doc, default=None):
        return __import__("jsonpointer").resolve_pointer(doc, self, default=default)


class Relativejsonpointer(wtypes.base.String, format="relative-json-pointer"):
    ...


class Regex(wtypes.base.String, format="regex"):
    for k in "compile match finditer findall subn sub split template".split():
        locals()[k] = getattr(re, k)
    del k
