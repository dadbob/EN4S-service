# -*- coding: utf-8 -*-
import core.users as cuser
import core.complaints as ccomp
import core.comments as ccomm
import core.gov as cgov

import json
import bcrypt

from functools import wraps

from flask import Flask, request, session
from flask import abort
from flask.ext import restful

from settings import db
import settings
import pymongo
from bson import ObjectId

# utils
from serviceutils import serialize_user, serialize_complaint
from serviceutils import get_location_from_city

app = Flask(__name__)
api = restful.Api(app)


def basic_authentication():
    return session.get('logged_in')


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(func, 'authenticated', True):
            return func(*args, **kwargs)

        acct = basic_authentication()
        if acct:
            return func(*args, **kwargs)

        restful.abort(401)
    return wrapper


def admin_authentication():
    user_type = session.get("user")["user_type"]
    if user_type == "admin":
        return True
    else:
        return False
    # return session["user"]["user_type"] is "admin"


def admin_authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(func, 'authenticated', True):
            return func(*args, **kwargs)

        acct = admin_authentication()
        if acct:
            return func(*args, **kwargs)

        restful.abort(401)
    return wrapper


class Hatirlat(restful.Resource):
    def post(self):
        data_dict = json.loads(request.data)
        db.hatirlat.insert(
            {
                "email": data_dict["email"]
            }
        )

        return "success", 200


class Login(restful.Resource):
    def post(self):
        data_dict = json.loads(request.data)

        email = unicode(data_dict['email'])
        pwd = unicode(data_dict["password"])

        current_city = data_dict.get("current_city", "")
        android_id = data_dict.get("android_notification", "")
        apple_id = data_dict.get("apple_notification", "")
        client = data_dict.get("client", "")

        return cuser.login_user(
            session, email, pwd, client,
            android_id, apple_id, current_city
        )


class Logout(restful.Resource):
    def post(self):

        session['user'] = None
        session['logged_in'] = False
        return {"success": "successfuly logged out"}, 200


class FacebookLogin(restful.Resource):
    def post(self):
        data_dict = json.loads(request.data)
        email = data_dict['email']
        access_token = data_dict['access_token']

        current_city = data_dict.get("current_city", "")
        android_id = data_dict.get("android_notification", "")
        apple_id = data_dict.get("apple_notification")

        return cuser.login_user_with_facebook(
            session, email, access_token,
            android_id, apple_id, current_city
        )


class Register(restful.Resource):
    def post(self):
        data_dict = json.loads(request.data)

        email = unicode(data_dict['email'])
        password = unicode(data_dict['password'])
        first_name = unicode(data_dict['first_name'])
        last_name = unicode(data_dict['last_name'])

        return cuser.register_user(
            session, email, password, first_name, last_name)


class ProfileUpdate(restful.Resource):
    def post(self):
        data_dict = json.loads(request.data)
        user = session.get("user")
        if not user:
            return abort(404)

        update_type = data_dict["type"]
        if update_type == "profile":
            userid = user["_id"]
            twitter = data_dict["twitter"]
            website = data_dict["website"]

            return cuser.update_profile_info(session, user, twitter, website)
        elif update_type == "password":
            userid = user["_id"]
            user = db.users.find_one({"email": unicode(user['email'])})

            if not user:
                return {'error': 'user not found'}, 404

            current_pwd = data_dict["current_pwd"]
            new_pwd = data_dict["new_pwd"]

            pwd_hash = user["password"]
            if bcrypt.hashpw(current_pwd, pwd_hash) != pwd_hash:
                return {'error': 'password is invalid'}, 404
            else:
                new_pwd_hash = bcrypt.hashpw(new_pwd, bcrypt.gensalt())
                db.users.update(
                    {"_id": ObjectId(userid)},
                    {"$set": {"password": new_pwd_hash}}
                )
                return 200

        return 402


class UserAll(restful.Resource):
    def get(self):
        users = db.users.find()
        serialized_users = []
        for user in users:
            temp_user = serialize_user(user)
            serialized_users.append(temp_user)

        return serialized_users, 200


class User(restful.Resource):
    def get(self, userslug):
        return cuser.get_user_with_slug(userslug)


class UpdateUserCity(restful.Resource):
    method_decorators = [authenticate]

    def put(self):
        data_dict = json.loads(request.data)
        current_city = unicode(data_dict['current_city'])

        user = session.get("user")
        return cuser.update_user_city(session, user, current_city)


class CityMeta(restful.Resource):
    def get(self, city):
        location = get_location_from_city(city)
        return (location, 200, {"Cache-Control": "no-cache"})


class City(restful.Resource):
    def get(self, city):
        l = []
        category = request.args.get('category', '')

        if category is "":
            category = "all"

        if category is not 'all':
            items = db.complaint.find(
                {"category": category, "slug_city": city}
            )

            items = items.sort("date", pymongo.DESCENDING)
        else:
            items = db.complaint.find(
                {"slug_city": city}
            ).sort("date", pymongo.DESCENDING)

        for item in items:
            comments = item.pop("comments")
            item["comments_count"] = len(comments)
            item.pop("user")
            item.pop("upvoters")
            item = serialize_complaint(item)
            l.append(item)

        return (l, 200, {"Cache-Control": "no-cache"})


class ComplaintHot(restful.Resource):
    def get(self):
        category = request.args.get('category', '')
        sinceid = request.args.get('sinceid', '')
        slug_city = request.args.get('slugcity', '')
        return ccomp.get_hot_complaints(category, sinceid, slug_city)


class ComplaintRecent(restful.Resource):
    def get(self):
        category = request.args.get('category', '')
        sinceid = request.args.get('sinceid', '')
        slug_city = request.args.get('slugcity', '')
        return ccomp.get_recent_complaints(category, sinceid, slug_city)


class ComplaintAll(restful.Resource):
    def get(self):
        category = request.args.get('category', '')
        slug_city = request.args.get('slugcity', '')
        return ccomp.get_all_complaints(category, slug_city)


class ComplaintTop(restful.Resource):
    def get(self):
        category = request.args.get('category', '')
        sinceid = request.args.get('sinceid', '')
        slug_city = request.args.get('slugcity', '')
        return ccomp.get_top_complaints(category, sinceid, slug_city)


class ComplaintNear(restful.Resource):
    def get(self):
        lati = request.args.get('latitude', '')
        longi = request.args.get('longitude', '')
        category = request.args.get('category', '')
        sinceid = request.args.get('sinceid', '')
        slug_city = request.args.get('slugcity', '')
        return ccomp.get_near_complaints(
            lati, longi, category, sinceid, slug_city)


class ComplaintNew(restful.Resource):
    method_decorators = [authenticate]

    def post(self):
        data_dict = json.loads(request.data.decode("utf-8"))
        location = data_dict['location']
        title = unicode(data_dict['title'])
        pic_arr = data_dict["pic_arr"]
        category = data_dict["category"]

        return ccomp.post_new_complaint(
            session, location, title, pic_arr, category)


class ComplaintUpvote(restful.Resource):
    method_decorators = [authenticate]

    def put(self, obj_id):
        return ccomp.upvote_complaint(session, obj_id)


class ComplaintDownvote(restful.Resource):
    method_decorators = [authenticate]

    def put(self, obj_id):
        return ccomp.downvote_complaint(session, obj_id)


class ComplaintSingle(restful.Resource):
    def get(self, obj_id):
        return ccomp.get_complaint_with_id(obj_id)


class ComplaintSingleSlug(restful.Resource):
    def get(self, city, slug):
        return ccomp.get_complaint_with_slug(city, slug)


class ComplaintDelete(restful.Resource):
    def post(self):
        data_dict = json.loads(request.data)
        picpath = data_dict["picpath"]
        complaint_id = data_dict["complaint_id"]
        return ccomp.delete_complaint(session, picpath, complaint_id)


class CommentsGet(restful.Resource):
    def get(self, complaint_id):
        obj_id = ObjectId(unicode(complaint_id))
        return ccomm.get_comments_from_complaint(obj_id)


class CommentsNew(restful.Resource):
    method_decorators = [authenticate]

    def put(self, complaint_id):
        data_dict = json.loads(request.data)
        text = data_dict["text"]
        return ccomm.put_new_comment(session, complaint_id, text)


class CommentsDelete(restful.Resource):
    method_decorators = [admin_authenticate]

    def post(self):
        data_dict = json.loads(request.data)
        complaint_id = data_dict["complaint_id"]
        comment_id = data_dict["comment_id"]
        return ccomm.delete_comment(complaint_id, comment_id)


class LoginGov(restful.Resource):
    def post(self):
        data_dict = json.loads(request.data)

        govname = unicode(data_dict.get("govname", ""))
        pwd = unicode(data_dict.get("password", ""))

        return cgov.login_gov(session, govname, pwd)


class LogoutGov(restful.Resource):
    def post(self):

        session['gov'] = None
        session['logged_in'] = False
        return {"success": "successfuly logged out"}, 200


# user resources
api.add_resource(Hatirlat, '/user/hatirlat')
api.add_resource(Login, '/user/login')
api.add_resource(Logout, '/user/logout')
api.add_resource(ProfileUpdate, '/user/profileupdate')
api.add_resource(FacebookLogin, '/user/login/facebook')
api.add_resource(Register, '/user/register')
api.add_resource(User, '/user/<string:userslug>')
api.add_resource(UserAll, '/user/all')
api.add_resource(UpdateUserCity, '/user/updatecity')

# complaint resources
api.add_resource(ComplaintNew, '/complaint/new')
api.add_resource(ComplaintDelete, '/complaint/delete')
api.add_resource(ComplaintSingle, '/complaint/<string:obj_id>')
api.add_resource(ComplaintSingleSlug, '/slug/<string:city>/<string:slug>')
api.add_resource(ComplaintUpvote, '/complaint/upvote/<string:obj_id>')
api.add_resource(ComplaintDownvote, '/complaint/downvote/<string:obj_id>')
api.add_resource(ComplaintRecent, '/complaint/recent')
api.add_resource(ComplaintHot, '/complaint/hot')
api.add_resource(ComplaintAll, '/complaint/all')
api.add_resource(ComplaintTop, '/complaint/top')
api.add_resource(ComplaintNear, '/complaint/near')

# city data
api.add_resource(City, '/<string:city>')
api.add_resource(CityMeta, '/<string:city>/citymeta')

# comments
api.add_resource(CommentsGet, '/comments/<string:complaint_id>')
api.add_resource(CommentsNew, '/comments/<string:complaint_id>')
api.add_resource(CommentsDelete, '/comments/delete')

# govs
api.add_resource(LoginGov, '/gov/login')
api.add_resource(LogoutGov, '/gov/logout')

if __name__ == '__main__':
    app.debug = settings.DEBUG
    app.secret_key = settings.SECRET
    app.run(host=settings.HOST, port=settings.PORT)
