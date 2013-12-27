# -*- coding: utf-8 -*-
import slugify
import re
import os
import base64
import requests

from PIL import Image
from settings import db
from bson import json_util
import json


def serialize_mongodb_object(mongo_dict):
    json_string = json_util.dumps(mongo_dict)
    json_object = json.loads(json_string)
    return json_object


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

        if "register_date" in obj:
            obj["register_date"] = unicode(
                obj["register_date"].strftime("%Y-%m-%d %H:%M:%S.%f")
            )

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


def byte_array_to_file(array, city, h):
    IMAGEFOLDER = "/srv/flask/en4s/pics/"
    URL = "/pics/"

    try:
        os.makedirs(IMAGEFOLDER + city + "/")
    except:
        pass

    # new_filename = IMAGEFOLDER + city + "/" +\
    #            hashlib.sha256(unicode(array)).hexdigest() + ".jpg"

    new_filename = IMAGEFOLDER + city + "/" + h + ".jpg"
    new_url = URL + city + "/" + h + ".jpg"

    array = base64.b64decode(array)

    file = open(new_filename, "wb")
    file.write(array)
    file.close()

    try:
        for size in [(512, 1000)]:
            thumbnail_path = IMAGEFOLDER + city + "/" + h + "." + str(size[0]) + ".jpg"
            im = Image.open(new_filename)
            im.thumbnail(size, Image.ANTIALIAS)
            im.save(thumbnail_path, "JPEG")
    except:
        print "couldn't save the thumbnails. sorry"

    return new_url


def complaint_to_device_id_list(complaint_id):
    """

    Arguments:
    - `complaint_id`:
    """
    complaint = db.complaint.find_one({"_id": complaint_id})
    upvoters = complaint.get("upvoters")
    downvoters = complaint.get("downvoters")

    voters = upvoters + downvoters

    device_ids = {"apple": [], "android": []}

    for voter in voters:
        voter_details = db.users.find_one({"_id": voter})
        if voter_details:
            voter_devices = voter_details.get("devices")
            if voter_devices:
                for device in voter_devices:
                    if "android" in device:
                        device_ids["android"].append(device["android"])
                    if "apple" in device:
                        device_ids["apple"].append(device["apple"])

    return device_ids
