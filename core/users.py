import requests

import bcrypt
import urllib
import hashlib

from settings import db
from serviceutils import make_slug, check_mail
from serviceutils import serialize_user, serialize_complaint

from bson import ObjectId
from datetime import datetime


def cleanup_user_for_session(user):
    """
    remove unnecessary user data from session,
    like passwords, complaints etc.

    Arguments:
    - `user`: user object that is returned from db.
    """
    pop_arr = ["password", "complaints",
               "upvotes", "downvotes"]
    for item in pop_arr:
        if item in user:
            user.pop(item, None)
    return user


def login_user(session, email, password, client,
               android_id="", apple_id="", current_city=""):
    """

    Arguments:
    - `email`:
    - `password`:
    - `android_id`:
    - `apple_id`:
    - `session`:
    """

    user = db.users.find_one(
        {"email": email}
    )

    if not user:
        return {"error": "wrong password/email combination"}, 401

    pwd_hash = user["password"]
    if bcrypt.hashpw(password, pwd_hash) != pwd_hash:
        return {"error": "wrong password/email combination"}, 401
    else:
        if android_id:
            db.users.update(
                {"_id": user["_id"]},
                {"$addToSet": {"devices": {"android": android_id}}}
            )
        elif apple_id:
            db.users.update(
                {"_id": user["_id"]},
                {"$addToSet": {"devices": {"apple": apple_id}}}
            )

        if current_city:
            db.users.update(
                {"_id": user["_id"]},
                {"$set": {"current_city": current_city}}
            )

        if client:
            db.users.update(
                {"_id": user["_id"]},
                {"$set": {"client": client}}
            )

        user = db.users.find_one(
            {"email": email}
        )

        user = cleanup_user_for_session(user)
        session['user'] = user
        session['logged_in'] = True
        user = serialize_user(user)

        return user, 200


def login_user_with_facebook(session, email, access_token,
                             android_id="", apple_id="", current_city=""):
    """

    Arguments:
    - `session`:
    - `email`:
    - `access_token`:
    """
    url = "https://graph.facebook.com/me?access_token=" + access_token
    r = requests.get(url)
    if r.status_code != 200:
        return {'error': "access token is not valid"}, 401
    else:
        user = db.users.find_one(
            {"email": email}
        )

        if not user:
            json_data = r.json()

            if "username" in json_data:
                username = json_data["username"]
            else:
                username = json_data["id"]

            if "email" in json_data:
                email = json_data["email"]
            else:
                email = username + "@facebook.com"

            avatar_url = "https://graph.facebook.com/"
            avatar_url += username
            avatar_url += "/picture?type=square&width=75&height=75"

            meta = db.metadata.find_one()
            user_count = int(meta["user_count"])
            user_count = str(user_count + 1)
            user_slug = make_slug(json_data["name"]) + "-" + user_count

            try:
                db.users.insert(
                    {
                        "email": email,
                        "first_name": json_data["first_name"],
                        "last_name": json_data["last_name"],
                        "name": json_data["name"],
                        "devices": [],
                        "current_city": "",
                        "complaints": [],
                        "upvotes": [],
                        "downvotes": [],
                        "fbusername": username,
                        "avatar": avatar_url,
                        "user_type": "member",
                        "user_slug": user_slug,
                        "fb": 1,
                        "register_date": datetime.now()
                    }
                )

                db.metadata.update(
                    {"type": "statistics"},
                    {"$inc": {"user_count": 1}}
                )

                user = db.users.find_one({"email": email})
                user = cleanup_user_for_session(user)
                session['user'] = user
                session['logged_in'] = True
                user = serialize_user(user)
                return user, 200
            except:
                return {'error': 'cont login with facebook'}, 400
        else:
            json_data = r.json()

            if user['fb'] == 0:
                if "username" in json_data:
                    username = json_data["username"]
                else:
                    username = json_data["id"]

                user['fbusername'] = username
                user['fb'] = 1
                db.users.save(user)

            if android_id:
                db.users.update(
                    {"_id": user["_id"]},
                    {"$addToSet": {"devices": {"android": android_id}}}
                )
            elif apple_id:
                db.users.update(
                    {"_id": user["_id"]},
                    {"$addToSet": {"devices": {"apple": apple_id}}}
                )

            if current_city:
                db.users.update(
                    {"_id": user["_id"]},
                    {"$set": {"current_city": current_city}}
                )

            user = db.users.find_one(
                {"email": email}
            )

            user = cleanup_user_for_session(user)
            session['user'] = user
            session['logged_in'] = True
            user = serialize_user(user)
            return user, 200


def register_user(session, email, password, first_name, last_name):
    """

    Arguments:
    - `session`:
    - `email`:
    - `password`:
    - `first_name`:
    - `last_name`:
    """

    name = first_name + " " + last_name
    password = bcrypt.hashpw(password, bcrypt.gensalt())

    default = "http://enforceapp.com/static/img/enforce-avatar-big.png"
    size = 75
    gravatar_url = "http://www.gravatar.com/avatar/" +\
                   hashlib.md5(email.lower()).hexdigest() + "?"

    gravatar_url += urllib.urlencode({'d': default, 's': str(size)})

    meta = db.metadata.find_one()
    user_count = int(meta["user_count"])
    user_count = str(user_count + 1)
    user_slug = make_slug(name) + "-" + user_count

    user = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "avatar": gravatar_url,
        "name": name,
        "complaints": [],
        "upvotes": [],
        "downvotes": [],
        "password": password,
        "user_type": "member",
        "user_slug": user_slug,
        "fb": 0,
        "register_date": datetime.now()
    }

    if not (email or password):
        return {'error': 'email or password is not given'}, 404
    else:
        if check_mail(email):

            db.users.insert(user)
            user = cleanup_user_for_session(user)

            session["user"] = user
            session["logged_in"] = True
            user = serialize_user(user)

            db.metadata.update(
                {"type": "statistics"},
                {"$inc": {"user_count": 1}}
            )

            return user, 201
        else:
            return {'error': "email address is not valid"}, 404


def get_user_with_slug(slug):
    """

    Arguments:
    - `slug`:
    """
    user = db.users.find_one({"user_slug": slug})
    if not user:
        return {"error": "user not found with that slug"}, 404

    user = serialize_user(user)
    cmps = []
    for complaint in user["complaints"]:
        temp_cmp = db.complaint.find_one({"_id": ObjectId(complaint)})
        if temp_cmp:
            temp_cmp.pop("user")
            comments = temp_cmp.pop("comments")
            temp_cmp["comments_count"] = len(comments)
            temp_cmp = serialize_complaint(temp_cmp)
            cmps.append(temp_cmp)
    user["complaints"] = cmps
    user["complaints"] = sorted(
        user["complaints"],
        key=lambda k: k["date"],
        reverse=True
    )

    upvts = []
    for upvote in user["upvotes"]:
        temp_upvote = db.complaint.find_one({"_id": ObjectId(upvote)})
        if temp_upvote:
            temp_upvote.pop("user")
            comments = temp_upvote.pop("comments")
            temp_upvote["comments_count"] = len(comments)
            temp_upvote = serialize_complaint(temp_upvote)
            upvts.append(temp_upvote)
    user["upvotes"] = upvts
    user["upvotes"] = sorted(
        user["upvotes"],
        key=lambda k: k["date"],
        reverse=True
    )

    return user, 200


def update_profile_info(session, user, twitter, website):
    """

    Arguments:
    - `session`:
    - `user`:
    - `twitter`:
    - `website`:
    """
    userid = user["_id"]

    db.users.update(
        {"_id": ObjectId(userid)},
        {"$set": {"twitter": twitter, "website": website}}
    )

    user = db.users.find_one({"_id": ObjectId(userid)})
    user = cleanup_user_for_session(user)
    session['user'] = user
    session['logged_in'] = True
    user = serialize_user(user)
    return user, 200


def update_user_not_settings(session, user, data_dict):
    for k, v in data_dict.iter():
        key = k
        val = v

    userid = user["_id"]
    key = "settings." + key

    db.users.update(
        {"_id": ObjectId(userid)},
        {"$set": {key: val}}
    )


def update_user_city(session, user, current_city):
    """

    Arguments:
    - `session`:
    - `user`:
    - `city`:
    """
    userid = user["_id"]
    db.users.update(
        {"_id": ObjectId(userid)},
        {"$set": {"current_city": current_city}}
    )
    user = db.users.find_one({"_id": ObjectId(userid)})
    user = cleanup_user_for_session(user)
    session['user'] = user
    session['logged_in'] = True
    user = serialize_user(user)
    return user, 202
