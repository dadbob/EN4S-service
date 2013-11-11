import bcrypt

from settings import db
from serviceutils import make_slug, check_mail
from serviceutils import serialize_user, serialize_complaint
from serviceutils import complaint_to_device_id_list

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


def fix_complaint(session, notification, complaint_id):
    """

    Arguments:
    - `session`:
    - `notification`:
    - `complaint_id`:
    """
    govname = session.get("gov")["govname"]
    # govtitle = session.get("title")

    if not govname:
        return {"error": "authentication required"}, 401

    if not complaint_id:
        return {"error": "complaint id required"}, 404

    complaint_id = ObjectId(complaint_id)

    db.complaint.update(
        {"_id": complaint_id},
        {"$set": {"status": "fixed"}}
    )

    # send notification here
    print complaint_to_device_id_list(complaint_id)

    return {"success": "action completed"}, 200


def accept_complaint(session, notification, complaint_id):
    """

    Arguments:
    - `session`:
    - `notification`:
    - `complaint_id`:
    """
    govname = session.get("govname")
    # govtitle = session.get("title")

    if not govname:
        return {"error": "authentication required"}, 401

    if not complaint_id:
        return {"error": "complaint id required"}, 404

    complaint_id = ObjectId(complaint_id)

    db.complaint.update(
        {"_id": complaint_id},
        {"$set": {"status": "accepted"}}
    )

    # send notification here
    print complaint_to_device_id_list(complaint_id)

    return {"success": "action completed"}, 200


def reject_complaint(session, notification, complaint_id):
    """

    Arguments:
    - `session`:
    - `notification`:
    - `complaint_id`:
    """
    govname = session.get("govname")
    # govtitle = session.get("title")

    if not govname:
        return {"error": "authentication required"}, 401

    if not complaint_id:
        return {"error": "complaint id required"}, 404

    complaint_id = ObjectId(complaint_id)

    db.complaint.update(
        {"_id": complaint_id},
        {"$set": {"status": "rejected"}}
    )

    # send notification here
    print complaint_to_device_id_list(complaint_id)

    return {"success": "action completed"}, 200
