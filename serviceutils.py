# -*- coding: utf-8 -*-
import slugify
import re
import requests


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

    if "downvoters" in obj:
        serialized_downvoters = []
        for downvoter in obj["downvoters"]:
            serialized_downvoters.append(unicode(downvoter))

        obj["downvoters"] = serialized_downvoters

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

        if "complaints" in obj:
            serialized_complaints = []
            complaints = obj["complaints"]
            for c in complaints:
                serialized_complaints.append(unicode(c))
            obj["complaints"] = serialized_complaints

        if "upvotes" in obj:
            serialized_upvotes = []
            upvotes = obj["upvotes"]
            for u in upvotes:
                serialized_upvotes.append(unicode(u))
            obj["upvotes"] = serialized_upvotes

        if "downvotes" in obj:
            serialized_downvotes = []
            downvotes = obj["downvotes"]
            for d in downvotes:
                serialized_downvotes.append(unicode(d))
            obj["downvotes"] = serialized_downvotes

    return obj


def check_mail(text):
    reg = re.compile(
        '[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})'
    )

    regMail = reg.match(text)
    if not regMail:
        return False
    else:
        return True


def get_city_and_address(location):
    """
    returns a tuple like (city, address)
    Arguments:
    - `location`: [lat, lng]
    """
    URL_BASE = "http://maps.googleapis.com/maps/api"
    URL_PATH = URL_BASE + "/geocode/json?latlng=%s,%s&sensor=false" \
        % (location[0], location[1])

    address = ""
    city = ""

    print URL_PATH
    r = requests.get(URL_PATH)
    if r.status_code == 200:
        result = r.json()
        address = result["results"][0]["formatted_address"]
        components = result["results"][0]["address_components"]
        for subdoc in components:
            if "administrative_area_level_1" in subdoc["types"]:
                city = subdoc["long_name"]
                city = city.replace(" Province", "")

        return (city, address)
    else:
        return None


def get_location_from_city(city):
    """

    Arguments:
    - `city`:
    """
    URL_BASE = "http://maps.googleapis.com/maps/api"
    URL_PATH = URL_BASE + "/geocode/json?address=%s+%s&sensor=false" \
        % (city, "turkey")

    r = requests.get(URL_PATH)
    if r.status_code == 200:
        result = r.json()
        lati = result["results"][0]["geometry"]["location"]["lat"]
        longi = result["results"][0]["geometry"]["location"]["lng"]

        location = [lati, longi]
        return location
    else:
        return None
