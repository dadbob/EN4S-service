# -*- coding: utf-8 -*-
import slugify


def make_slug(text):
    return slugify.slugify(text.replace(u"ı", u"i"))


def serialize_complaint(item):
    obj = item

    obj["_id"] = unicode(obj["_id"])
    obj["date"] = unicode(obj["date"].strftime("%Y-%m-%d %H:%M:%S.%f"))

    if "upvoters" in obj:
        serialized_upvoters = []
        for upvoter in obj["upvoters"]:
            serialized_upvoters.append(unicode(upvoter))

        obj["upvoters"] = serialized_upvoters

    if "comments" in obj:
        for comment in obj["comments"]:
            comment["_id"] = unicode(comment["_id"])
            comment["date"] = unicode(
                comment["date"].strftime("%Y-%m-%d %H:%M:%S.%f")
            )

    return obj


def serialize_user(item):
    obj = item
    if obj:
        obj.pop("password", None)
        obj["_id"] = unicode(obj["_id"])
    return obj
