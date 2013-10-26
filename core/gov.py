import requests

import bcrypt
import urllib
import hashlib

from settings import db
from serviceutils import make_slug, check_mail
from serviceutils import serialize_user, serialize_complaint

from bson import ObjectId


def serialize_gov(item):
    obj = item
    if obj:
        obj.pop("password", None)
        obj["_id"] = unicode(obj["_id"])
    return obj


def login_gov(session, govname, password):
    """

    Arguments:
    - `email`:
    - `password`:
    - `android_id`:
    - `apple_id`:
    - `session`:
    """

    gov = db.govs.find_one({"govname": govname})
    if not gov:
        print "gov not found"
        return {"error": "wrong password/username combination"}, 401

    print password
    print gov["password"]

    pwd_hash = gov["password"]
    if bcrypt.hashpw(password, pwd_hash) != pwd_hash:
        print "pass didn't match"
        return {"error": "wrong password/username combination"}, 401
    else:
        session['gov'] = gov
        gov = serialize_gov(gov)
        return gov, 200
