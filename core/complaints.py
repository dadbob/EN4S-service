import pymongo
import os

from settings import db

from serviceutils import make_slug, get_city_and_address
from serviceutils import serialize_complaint, serialize_user
from serviceutils import byte_array_to_file

from bson import ObjectId
from datetime import datetime
from operator import itemgetter


def get_sinceid(since_id, sorted_list):
    if since_id == "":
        return sorted_list[:12]
    else:
        try:
            since_index = map(itemgetter('_id'), sorted_list).index(since_id)
            since_index = int(since_index)
            return (sorted_list[since_index + 1:since_index + 4], 200)
        except:
            return ([], 404)


def filter_with_category_and_city(category, slug_city, sorting_option="date"):
    """
    """

    if category == "" or category is None:
        category = "all"

    if slug_city == "" or slug_city is None:
        slug_city = "all"

    if category != 'all' and slug_city != 'all':
        items = db.complaint.find(
            {"category": category, "slug_city": slug_city}
        )
        items = items.sort(sorting_option, pymongo.DESCENDING)
    elif category != 'all':
        items = db.complaint.find(
            {"category": category}
        )
        items = items.sort(sorting_option, pymongo.DESCENDING)
    elif slug_city != 'all':
        items = db.complaint.find(
            {"slug_city": slug_city}
        )
        items = items.sort(sorting_option, pymongo.DESCENDING)
    else:
        items = db.complaint.find().sort(sorting_option, pymongo.DESCENDING)

    return items


def post_new_complaint(session, location, title, pic_arr, category):
    """

    Arguments:
    - `session`:
    - `location`:
    - `title`:
    - `pic_arr`:
    - `category`:
    """
    user = session.get("user")
    address_info = get_city_and_address(location)
    city = address_info[0]
    address = address_info[1]

    slug_city = make_slug(city)
    slug_title = make_slug(title)

    number = db.metadata.find_one({"type": "statistics"})
    number = int(number["complaint_count"])
    number += 1

    slug_url = "/" + slug_city + "/" + slug_title + "-" + str(number)
    public_url = "/" + slug_city + "/" + slug_title + "-" + str(number)

    filename = byte_array_to_file(
        pic_arr, slug_city,
        slug_title + "-" + str(number)
    )

    new_complaint = {
        "_id": ObjectId(),
        "title": title,
        "user": ObjectId(user["_id"]),
        "pics": [filename],
        "slug_city": slug_city,
        "slug_url": slug_url,
        "public_url": public_url,
        "category": category,
        "comments": [],
        "upvoters": [user["_id"]],
        "downvoters": [],
        "upvote_count": 1,
        "downvote_count": 0,
        "location": location,
        "address": address,
        "city": city,
        "date": datetime.now()
    }

    user = session.get("user")
    db.complaint.insert(new_complaint)

    new_complaint = serialize_complaint(new_complaint)
    new_complaint["user"] = serialize_user(user)
    new_complaint["comments_count"] = 0

    db.metadata.update(
        {"type": "statistics"},
        {"$inc": {"complaint_count": 1}}
    )

    db.users.update(
        {"_id": ObjectId(user["_id"])},
        {
            "$addToSet": {
                "complaints": ObjectId(new_complaint["_id"]),
                "upvotes": ObjectId(new_complaint["_id"])
            }
        }
    )

    return new_complaint, 201


def get_hot_complaints(category, sinceid, slug_city):
    """

    Arguments:
    - `session`:
    - `category`:
    - `sinceid`:
    - `city`:
    """
    current_time = datetime.now()
    l = []

    items = filter_with_category_and_city(category, slug_city)
    items = items[:50]      # limit 50 before sorting with scores
    for item in items:
        complaint_time = item["date"]
        delta = (current_time - complaint_time).days

        uc = item["upvote_count"]
        dc = item["downvote_count"]

        if delta == 0:
            item["score"] = 7 * (uc - dc)
            item["score"] += 2 * len(item["comments"])
        elif delta == 1:
            item["score"] = 6 * (uc - dc)
            item["score"] += len(item["comments"])
        elif delta == 2:
            item["score"] = 5 * (uc - dc)
            item["score"] += len(item["comments"])
        elif delta == 3:
            item["score"] = 4 * (uc - dc)
            item["score"] += len(item["comments"])
        elif delta > 3 and delta <= 15:
            item["score"] = (uc - dc)
            item["score"] += len(item["comments"])
        elif delta > 15 and delta <= 30:
            item["score"] = 0.8 * (uc - dc)
        elif delta > 30 and delta <= 60:
            item["score"] = 0.4 * (uc - dc)
        elif delta > 60 and delta <= 120:
            item["score"] = 0.2 * (uc - dc)
        else:
            item["score"] = 0.1 * (uc - dc)

        if int(item["downvote_count"]) >= int(item["upvote_count"]):
            item["score"] = 0

        comments = item.pop("comments")
        item["comments_count"] = len(comments)
        item = serialize_complaint(item)
        item["user"] = db.users.find_one({"_id": item["user"]})
        item["user"] = serialize_user(item["user"])
        l.append(item)

    sorted_l = sorted(l, key=lambda x: x["score"], reverse=True)

    if sinceid == "":
        sorted_l = (sorted_l[:12], 200)
    else:
        sorted_l = get_sinceid(sinceid, sorted_l)

    return sorted_l


def get_recent_complaints(category, sinceid, slug_city, sorting_option="date"):
    """

    Arguments:
    - `session`:
    - `category`:
    - `sinceid`:
    - `slug_city`:
    """
    items = filter_with_category_and_city(category, slug_city)
    items = items[:50]

    l = []
    for item in items:
        comments = item.pop("comments")
        item["comments_count"] = len(comments)
        item = serialize_complaint(item)
        item["user"] = db.users.find_one({"_id": item["user"]})
        item["user"] = serialize_user(item["user"])
        l.append(item)

    if sinceid == "":
        l = (l[:12], 200)
    else:
        l = get_sinceid(sinceid, l)

    return l


def get_all_complaints(category, slug_city):
    """

    Arguments:
    - `category`:
    - `slug_city`:
    """
    items = filter_with_category_and_city(category, slug_city)
    l = []
    for item in items:
        comments = item.pop("comments")
        item["comments_count"] = len(comments)
        item = serialize_complaint(item)
        item["user"] = db.users.find_one({"_id": item["user"]})
        item["user"] = serialize_user(item["user"])
        l.append(item)

    return l


def get_top_complaints(category, sinceid, slug_city):
    """

    Arguments:
    - `category`:
    - `slug_city`:
    """
    items = filter_with_category_and_city(
        category, slug_city, sorting_option="upvote_count"
    )
    l = []
    for item in items:
        comments = item.pop("comments")
        item["comments_count"] = len(comments)
        item = serialize_complaint(item)
        item["user"] = db.users.find_one({"_id": item["user"]})
        item["user"] = serialize_user(item["user"])
        l.append(item)

    if sinceid == "":
        l = (l[:12], 200)
    else:
        l = get_sinceid(sinceid, l)

    return l


def get_near_complaints(lati, longi, category, sinceid, slug_city):
    """

    Arguments:
    - `category`:
    - `slug_city`:
    - `sinceid`:
    """
    l = []
    if category is "":
        category = "all"

    loc = [float(lati), float(longi)]
    if category is not 'all':
        items = db.complaint.find({"category": category,
                                   "location": {"$near": loc}})
    else:
        items = db.complaint.find({"location": {"$near": loc}})

    items = items[:50]      # limit 10 item

    for item in items:
        comments = item.pop("comments")
        item["comments_count"] = len(comments)
        item = serialize_complaint(item)
        item["user"] = db.users.find_one({"_id": item["user"]})
        item["user"] = serialize_user(item["user"])
        l.append(item)

    if sinceid == "":
        l = (l[:12], 200)
    else:
        l = get_sinceid(sinceid, l)

    return l


def upvote_complaint(session, obj_id):
    """

    Arguments:
    - `session`:
    - `obj_id`:
    """

    obj_id = ObjectId(unicode(obj_id))
    obj = db.complaint.find_one({"_id": obj_id})
    if not obj:
        return {"error": "object id not found"}, 404

    upvoters = obj["upvoters"]
    downvoters = obj["downvoters"]

    user = session["user"]
    if not user:
        return {"error": "user not found in the session"}, 404
    user_id = ObjectId(user["_id"])

    if user_id in upvoters:
        # remove users upvote
        db.complaint.update(
            {"_id": obj_id},
            {"$pull": {"upvoters": user_id}}
        )

        db.complaint.update(
            {"_id": obj_id}, {"$inc": {"upvote_count": -1}}
        )

        db.users.update(
            {"_id": user_id},
            {"$pull": {"upvotes": obj_id}}
        )

        obj = db.complaint.find_one({"_id": obj_id})
        comments = obj.pop("comments")
        obj["comments_count"] = len(comments)
        obj = serialize_complaint(obj)
        obj["user"] = db.users.find_one({"_id": obj["user"]})
        obj["user"] = serialize_user(obj["user"])
        return obj, 202
    elif user_id in downvoters:
        return {"error": "user downvoted this. can't upvote."}, 406

    db.complaint.update(
        {"_id": obj_id},
        {"$addToSet": {"upvoters": user_id}}
    )

    db.complaint.update(
        {"_id": obj_id}, {"$inc": {"upvote_count": 1}}
    )

    db.users.update(
        {"_id": user_id},
        {"$addToSet": {"upvotes": obj_id}}
    )

    obj = db.complaint.find_one({"_id": obj_id})
    comments = obj.pop("comments")
    obj["comments_count"] = len(comments)
    obj = serialize_complaint(obj)
    obj["user"] = db.users.find_one({"_id": obj["user"]})
    obj["user"] = serialize_user(obj["user"])

    return obj, 202


def downvote_complaint(session, obj_id):
    """

    Arguments:
    - `session`:
    - `obj_id`:
    """

    obj_id = ObjectId(unicode(obj_id))
    obj = db.complaint.find_one({"_id": obj_id})
    if not obj:
        return {"error": "object id not found"}, 404

    upvoters = obj["upvoters"]
    downvoters = obj["downvoters"]

    user = session["user"]
    if not user:
        return {"error": "user not found in session"}, 404
    user_id = ObjectId(user["_id"])

    if user_id in upvoters:
        return {"error": "user upvoted this. can't downvote."}, 406
    elif user_id in downvoters:
        # remove users upvote
        db.complaint.update(
            {"_id": obj_id},
            {"$pull": {"downvoters": user_id}}
        )

        db.complaint.update(
            {"_id": obj_id}, {"$inc": {"downvote_count": -1}}
        )

        db.users.update(
            {"_id": user_id},
            {"$pull": {"downvotes": obj_id}}
        )

        obj = db.complaint.find_one({"_id": obj_id})
        comments = obj.pop("comments")
        obj["comments_count"] = len(comments)
        obj = serialize_complaint(obj)
        obj["user"] = db.users.find_one({"_id": obj["user"]})
        obj["user"] = serialize_user(obj["user"])
        return obj, 202

    db.complaint.update(
        {"_id": obj_id},
        {"$addToSet": {"downvoters": user_id}}
    )

    db.complaint.update(
        {"_id": obj_id}, {"$inc": {"downvote_count": 1}}
    )

    db.users.update(
        {"_id": user_id},
        {"$addToSet": {"downvotes": obj_id}}
    )

    obj = db.complaint.find_one({"_id": obj_id})
    comments = obj.pop("comments")
    obj["comments_count"] = len(comments)
    obj = serialize_complaint(obj)
    obj["user"] = db.users.find_one({"_id": obj["user"]})
    obj["user"] = serialize_user(obj["user"])
    return obj, 202


def get_complaint_with_id(obj_id):
    """

    Arguments:
    - `obj_id`:
    """
    obj_id = ObjectId(unicode(obj_id))
    obj = db.complaint.find_one({"_id": obj_id})

    if not obj:
        return {"error": "object id not found"}, 404

    obj = serialize_complaint(obj)
    obj["user"] = db.users.find_one({"_id": obj["user"]})
    obj["user"] = serialize_user(obj["user"])

    for comment in obj["comments"]:
        comment["author"] = db.users.find_one({
            "_id": ObjectId(comment["author"])
        })
        comment["author"] = serialize_user(comment["author"])

    return obj, 200


def get_complaint_with_slug(city, slug):
    """

    Arguments:
    - `city`:
    - `slug`:
    """
    path = "/" + city + "/" + slug
    obj = db.complaint.find_one({"slug_url": path})

    if not obj:
        return {"error": "city/slug combination not found"}, 404

    obj = serialize_complaint(obj)
    obj["user"] = db.users.find_one({"_id": obj["user"]})
    obj["user"] = serialize_user(obj["user"])

    for comment in obj["comments"]:
        comment["author"] = db.users.find_one({
            "_id": ObjectId(comment["author"])
        })
        comment["author"] = serialize_user(comment["author"])

    return obj, 200


def delete_complaint(session, picpath, complaint_id):
    """

    Arguments:
    - `session`:
    - `picpath`:
    - `complaint_id`:
    """

    picpath512 = picpath.replace(".jpg", ".512.jpg")
    path = "/srv/flask/en4s"

    obj_id = ObjectId(unicode(complaint_id))
    obj = db.complaint.find_one({"_id": obj_id})

    request_user = session.get("user")

    if not request_user:
        return {"error": "authentication failed"}, 405

    flag_owner = request_user["_id"] == unicode(obj["user"])
    flag_admin = request_user["user_type"] == "admin"

    if not (flag_owner or flag_admin):
        return {"error": "not admin or owner"}, 405
    else:
        db.metadata.update(
            {"type": "statistics"},
            {"$inc": {"complaint_count": -1}}
        )

        db.users.update(
            {"_id": obj["user"]},
            {"$pull": {"complaints": obj["_id"]}}
        )

        db.users.update(
            {"upvotes": obj["_id"]},
            {"$pull": {"upvotes": obj["_id"]}},
            multi=True
        )

        db.users.update(
            {"downvotes": obj["_id"]},
            {"$pull": {"downvotes": obj["_id"]}},
            multi=True
        )

        db.complaint.remove({"_id": obj_id})
        try:
            os.remove(path + picpath)
            os.remove(path + picpath512)
            # print db.complaint.find_one({"_id": obj_id})
            return {"success": "content deleted"}, 204
        except:
            return {"error": "something bad happened on delete"}, 404
