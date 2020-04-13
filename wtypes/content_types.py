import wtypes


class _Content(wtypes.String):
    def _repr_data_(self):
        print([x for x in type(self).__mro__])
        return {
            x._schema.contentMediaType: self
            for x in type(self).__mro__
            if getattr(x, "_schema", None) and "contentMediaType" in x._schema
        }

    def _repr_metadata_(self):
        return {}

    def _repr_mimebundle_(self, include=None, exclude=None):
        return self._repr_data_(), self._repr_metadata_()


class TextPlain(_Content, ContentMediaType="text/plain"):
    ...


class TextMarkdown(TextPlain, contentMediaType="text/markdown"):
    ...


class TextHtml(TextPlain, contentMediaType="text/html"):
    ...
