# -*- coding: utf-8 -*-
from settings import db
from serviceutils import serialize_user

from bson import ObjectId
from datetime import datetime


def get_comments_from_complaint(complaint_id):
    """

    Arguments:
    - `complaint_id`:
    """
    complaint_obj = db.complaint.find_one({"_id": complaint_id})
    if not complaint_obj:
        return {'error': 'complaint not found'}, 404

    comments = []

    for comment in complaint_obj["comments"]:
        try:
            comment["date"] = str(comment["date"])
            comment["_id"] = str(comment["_id"])
            comment["author"] = db.users.find_one(
                {"_id": ObjectId(comment["author"])}
            )
            comment["author"] = serialize_user(comment["author"])
            comments.append(comment)
        except:
            pass
    return comments, 200


def put_new_comment(session, complaint_id, text):
    """

    Arguments:
    - `session`:
    - `complaint_id`:
    - `text`:
    """
    user = session.get("user")

    obj_id = ObjectId(unicode(complaint_id))
    complaint_obj = db.complaint.find_one({"_id": obj_id})
    if not complaint_obj:
        return {'error': 'complaint not found'}, 404

    comment_data = {}
    comment_data["_id"] = ObjectId()
    comment_data["date"] = datetime.now()
    comment_data["author"] = user["_id"]
    comment_data["text"] = text
    comment_data["like"] = 0
    comment_data["dislike"] = 0

    db.complaint.update(
        {"_id": obj_id},
        {"$addToSet": {"comments": comment_data}}
    )

    db.metadata.update(
        {"type": "statistics"},
        {"$inc": {"comment_count": 1}}
    )

    comment_data["date"] = str(comment_data["date"])
    comment_data["_id"] = str(comment_data["_id"])
    comment_data["author"] = db.users.find_one(
        {"_id": ObjectId(comment_data["author"])}
    )
    comment_data["author"] = serialize_user(comment_data["author"])

    return comment_data, 201


def delete_comment(complaint_id, comment_id):
    """

    Arguments:
    - `complaint_id`:
    - `comment_id`:
    """

    db.complaint.update(
        {"_id": ObjectId(complaint_id)},
        {"$pull": {"comments": {"_id": ObjectId(comment_id)}}}
    )

    db.metadata.update(
        {"type": "statistics"},
        {"$inc": {"comment_count": -1}}
    )

    return 200
