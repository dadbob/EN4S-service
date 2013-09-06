import os
import json
import base64
import requests
import bcrypt

from datetime import datetime
from functools import wraps

from flask import Flask, request, session
from flask import abort
from flask.ext import restful

from settings import db
import settings
import pymongo
from bson import ObjectId

# resize
from PIL import Image

# utils
from serviceutils import serialize_user, serialize_complaint
from serviceutils import check_mail, make_slug, get_city_and_address

# gravatar needings
import hashlib, urllib

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
        user = db.users.find_one(
            {"email": unicode(data_dict['email'])}
        )

        if not user:
            return {'error': 'user not found'}, 404

        pwd = unicode(data_dict["password"])
        pwd_hash = user["password"]
        if bcrypt.hashpw(pwd, pwd_hash) != pwd_hash:
            return {'error': 'password is invalid'}, 404
        else:
            user.pop("password", None)
            session['user'] = user
            session['logged_in'] = True
            user = serialize_user(user)
            return user, 200


class Logout(restful.Resource):
    def post(self):

        session['user'] = None
        session['logged_in'] = False
        return {"success": "successfuly logged out"}, 200

            # return {"error": "something bad happened"}, 404


class FacebookLogin(restful.Resource):
    def post(self):
        data_dict = json.loads(request.data)
        email = data_dict['email']
        access_token = data_dict['access_token']

        url = "https://graph.facebook.com/me?access_token=" + access_token
        r = requests.get(url)
        if r.status_code != 200:
            return {'error': 'cont login with facebook'}, 400
        else:
            user = db.users.find_one(
                {"email": email}
            )

            if not user:
                json_data = r.json()

                if "email" in json_data:
                    email = json_data["email"]
                else:
                    email = json_data["username"] + "@facebook.com"

                avatar_url = "https://graph.facebook.com/"
                avatar_url += json_data["username"]
                avatar_url += "/picture?type=square&width=75&height=75"

                try:
                    db.users.insert(
                        {
                            "email": email,
                            "first_name": json_data["first_name"],
                            "last_name": json_data["last_name"],
                            "name": json_data["name"],
                            "fbusername": json_data["username"],
                            "avatar": avatar_url,
                            "user_type": "member",
                            "fb": 1
                        }
                    )

                    db.metadata.update(
                        {"type": "statistics"},
                        {"$inc": {"user_count": 1}}
                    )

                    user = db.users.find_one({"email": email})
                    session['user'] = user
                    session['logged_in'] = True
                    user["_id"] = unicode(user["_id"])
                    return user, 200
                except:
                    print "[debug] en4s.py line 145"
                    return {'error': 'cont login with facebook'}, 400
            else:
                if user['fb'] == 0:
                    user['fbusername'] = json_data["username"]
                    user['fb'] = 1
                    db.users.save(user)

                session['user'] = user
                session['logged_in'] = True
                user["_id"] = unicode(user["_id"])
                return user, 200


class Register(restful.Resource):
    # todo validate email

    def post(self):
        data_dict = json.loads(request.data)

        email = unicode(data_dict['email'])
        first_name = unicode(data_dict['first_name'])
        last_name = unicode(data_dict['last_name'])
        name = first_name + " " + last_name
        password = unicode(data_dict['password'])
        password = bcrypt.hashpw(password, bcrypt.gensalt())

        default = "http://enforceapp.com/static/img/enforce-avatar-small.png"
        size = 75
        gravatar_url = "http://www.gravatar.com/avatar/" +\
                       hashlib.md5(email.lower()).hexdigest() + "?"

        gravatar_url += urllib.urlencode({'d': default, 's': str(size)})

        user = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "avatar": gravatar_url,
            "name": name,
            "password": password,
            "user_type": "member",
            "fb": 0
        }

        if not (email or password):
            return {'error': 'email or password not given'}, 404
        else:
            if check_mail(email):
                try:
                    db.users.insert(user)
                    user.pop("password", None)
                    session["user"] = user
                    session["logged_in"] = True
                    user = serialize_user(user)

                    db.metadata.update(
                        {"type": "statistics"},
                        {"$inc": {"user_count": 1}}
                    )

                    return user, 201
                except:
                    return {'error': "can't register"}, 404
            else:
                return {'error': "mail address is not valid"}, 404


class ComplaintHot(restful.Resource):
    def get(self):

        current_time = datetime.now()

        l = []
        category = request.args.get('category', '')

        if category is "":
            category = "all"

        if category is not 'all':
            items = db.complaint.find({"category": category})
            items = items.sort("date", pymongo.DESCENDING)
        else:
            items = db.complaint.find().sort("date", pymongo.DESCENDING)

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
                item["score"] = 5 * (uc - dc)
                item["score"] += len(item["comments"])
            elif delta == 2:
                item["score"] = 3 * (uc - dc)
                item["score"] += len(item["comments"])
            elif delta == 3:
                item["score"] = 2 * (uc - dc)
                item["score"] += len(item["comments"])
            else:
                item["score"] = (uc - dc)
                item["score"] += len(item["comments"])

            if int(item["downvote_count"]) >= int(item["upvote_count"]):
                item["score"] = 0

            comments = item.pop("comments")
            item["comments_count"] = len(comments)
            item = serialize_complaint(item)
            item["user"] = db.users.find_one({"_id": item["user"]})
            item["user"] = serialize_user(item["user"])
            l.append(item)

        sorted_l = sorted(l, key=lambda x: x["score"], reverse=True)
        sorted_l = sorted_l[:12]

        return (sorted_l, 200, {"Cache-Control": "no-cache"})


class ComplaintRecent(restful.Resource):
    def get(self):
        l = []
        category = request.args.get('category', '')

        if category is "":
            category = "all"

        if category is not 'all':
            items = db.complaint.find({"category": category})
            items = items.sort("date", pymongo.DESCENDING)
        else:
            items = db.complaint.find().sort("date", pymongo.DESCENDING)

        items = items[:12]      # limit 10 item

        for item in items:
            comments = item.pop("comments")
            item["comments_count"] = len(comments)
            item = serialize_complaint(item)
            item["user"] = db.users.find_one({"_id": item["user"]})
            item["user"] = serialize_user(item["user"])
            l.append(item)

        return (l, 200, {"Cache-Control": "no-cache"})


class ComplaintAll(restful.Resource):
    def get(self):
        l = []
        category = request.args.get('category', '')

        if category is "":
            category = "all"

        if category is not 'all':
            items = db.complaint.find({"category": category})
            items = items.sort("date", pymongo.DESCENDING)
        else:
            items = db.complaint.find().sort("date", pymongo.DESCENDING)

        for item in items:
            # comments = item.pop("comments")
            # item["comments_count"] = len(comments)
            item = serialize_complaint(item)
            item["user"] = db.users.find_one({"_id": item["user"]})
            item["user"] = serialize_user(item["user"])
            l.append(item)

        return (l, 200, {"Cache-Control": "no-cache"})


class ComplaintTop(restful.Resource):
    def get(self):
        l = []
        category = request.args.get('category', '')

        if category is "":
            category = "all"

        if category is not 'all':
            items = db.complaint.find({"category": category})
            items = items.sort("upvote_count", pymongo.DESCENDING)
        else:
            items = db.complaint.find().sort("upvote_count",
                                             pymongo.DESCENDING)

        items = items[:12]      # limit 10 item

        for item in items:
            comments = item.pop("comments")
            item["comments_count"] = len(comments)
            item = serialize_complaint(item)
            item["user"] = db.users.find_one({"_id": item["user"]})
            item["user"] = serialize_user(item["user"])
            l.append(item)

        return (l, 200, {"Cache-Control": "no-cache"})


class ComplaintNear(restful.Resource):
    # method_decorators = [authenticate]

    def get(self):
        l = []

        lati = request.args.get('latitude', '')
        longi = request.args.get('longitude', '')
        category = request.args.get('category', '')

        if category is "":
            category = "all"

        loc = [float(lati), float(longi)]
        if category is not 'all':
            items = db.complaint.find({"category": category,
                                       "location": {"$near": loc}})
        else:
            items = db.complaint.find({"location": {"$near": loc}})

        items = items[:12]      # limit 10 item

        for item in items:
            comments = item.pop("comments")
            item["comments_count"] = len(comments)
            item = serialize_complaint(item)
            item["user"] = db.users.find_one({"_id": item["user"]})
            item["user"] = serialize_user(item["user"])
            l.append(item)

        return (l, 200, {"Cache-Control": "no-cache"})


class Complaint(restful.Resource):
    # todo new_complaint olusturmaya gerek yok
    # direk request.data'ya olmayan verileri ekle
    # ve database'e ekle

    method_decorators = [authenticate]

    def get(self):
        l = []
        for item in db.complaint.find():
            item["_id"] = unicode(item["_id"])
            item["date"] = unicode(item["date"])
            l.append(item)

        return (l, 200, {"Cache-Control": "no-cache"})

    def post(self):
        user = session["user"]
        data_dict = json.loads(request.data.decode("utf-8"))

        # userid = unicode(user["_id"])
        category = unicode(data_dict['category'])
        location = data_dict['location']

        address_info = get_city_and_address(location)
        city = address_info[0]
        address = address_info[1]
        # address = unicode(data_dict['address'])
        # city = unicode(data_dict['city'])
        title = unicode(data_dict['title'])
        complaint_id = ObjectId()
        slug_city = make_slug(city)
        slug_title = make_slug(title)
        public_url = "/complaint/" + slug_city + "/" + slug_title + "/" + str(unicode(complaint_id))

        number = db.metadata.find_one({"type": "statistics"})
        number = int(number["complaint_count"])
        number += 1
        slug_url = "/" + slug_city + "/" + slug_title + "-" + str(number)
        new_complaint = {
            "_id": complaint_id,
            "title": title,
            "user": ObjectId(user["_id"]),
            "pics": [],
            "slug_url": slug_url,
            "public_url": public_url,
            "category": category,
            "comments": [],
            "upvoters": [user["_id"]],
            "upvote_count": 1,
            "downvote_count": 0,
            "location": location,
            "address": address,
            "city": city,
            "date": datetime.now()
        }

        user = session.get("user")

        db.complaint.insert(new_complaint)
        new_complaint["_id"] = unicode(complaint_id)
        new_complaint["user"] = user
        new_complaint["user"]["_id"] = unicode(user["_id"])
        new_complaint["_id"] = unicode(new_complaint["_id"])
        new_complaint["date"] = unicode(new_complaint["date"])
        new_complaint["upvoters"][0] = unicode(new_complaint["upvoters"][0])
        print "[debug] before return new complaint"
        print "new complaint: "
        print new_complaint

        db.metadata.update(
            {"type": "statistics"},
            {"$inc": {"complaint_count": 1}}
        )

        return new_complaint, 201


class ComplaintPicture(restful.Resource):
    # todo base64 olarak degil
    # file objesi olarak almak daha verimli olacak.
    method_decorators = [authenticate]

    def post(self, obj_id):
        data_dict = json.loads(request.data)
        obj_id = ObjectId(unicode(obj_id))
        obj = db.complaint.find_one({"_id": obj_id})
        if not obj:
            return abort(404)
        city = unicode(obj["city"])
        city = make_slug(city)

        arr = data_dict["pic"]  # base 64 encoded
        h = data_dict["hash"]  # hash of the pic

        filename = byte_array_to_file(arr, city, h)

        db.complaint.update(
            {"_id": obj_id}, {"$addToSet": {"pics": filename}}
        )

        return {'path': str(filename)}, 201


class ComplaintUpvote(restful.Resource):
    method_decorators = [authenticate]

    def put(self, obj_id):
        obj_id = ObjectId(unicode(obj_id))
        obj = db.complaint.find_one({"_id": obj_id})
        if not obj:
            return abort(404)

        upvoters = obj["upvoters"]
        if session["user"]["_id"] in upvoters:
            return {"error": "user already upvoted"}, 406

        db.complaint.update(
            {"_id": obj_id},
            {"$addToSet": {"upvoters": session["user"]["_id"]}}
        )
        db.complaint.update(
            {"_id": obj_id}, {"$inc": {"upvote_count": 1}}
        )

        db.metadata.update(
            {"type": "statistics"},
            {"$inc": {"upvote_count": 1}}
        )

        return {"success": "upvote accepted"}, 202


class ComplaintDownvote(restful.Resource):
    method_decorators = [authenticate]

    def put(self, obj_id):
        obj_id = ObjectId(unicode(obj_id))
        obj = db.complaint.find_one({"_id": obj_id})
        if not obj:
            return abort(404)

        upvoters = obj["upvoters"]
        if session["user"]["_id"] in upvoters:
            return {"error": "user already voted"}, 406

        db.complaint.update(
            {"_id": obj_id},
            {"$addToSet": {"upvoters": session["user"]["_id"]}}
        )
        db.complaint.update(
            {"_id": obj_id}, {"$inc": {"downvote_count": 1}}
        )
        return {"success": "upvote accepted"}, 202


class ComplaintSingle(restful.Resource):
    def get(self, obj_id):
        obj_id = ObjectId(unicode(obj_id))
        obj = db.complaint.find_one({"_id": obj_id})

        if not obj:
            return abort(404)

        obj = serialize_complaint(obj)
        obj["user"] = db.users.find_one({"_id": obj["user"]})
        obj["user"] = serialize_user(obj["user"])

        for comment in obj["comments"]:
            comment["author"] = db.users.find_one({
                "_id": ObjectId(comment["author"])
            })
            comment["author"] = serialize_user(comment["author"])

        return obj


class ComplaintSingleSlug(restful.Resource):
    def get(self, city, slug):
        path = "/" + city + "/" + slug
        obj = db.complaint.find_one({"slug_url": path})

        if not obj:
            return abort(404)

        obj = serialize_complaint(obj)
        obj["user"] = db.users.find_one({"_id": obj["user"]})
        obj["user"] = serialize_user(obj["user"])

        for comment in obj["comments"]:
            comment["author"] = db.users.find_one({
                "_id": ObjectId(comment["author"])
            })
            comment["author"] = serialize_user(comment["author"])

        return obj


class ComplaintDelete(restful.Resource):
    method_decorators = [admin_authenticate]

    def post(self):
        data_dict = json.loads(request.data)
        picpath = data_dict["picpath"]
        complaint_id = data_dict["complaint_id"]

        picpath512 = picpath.replace(".jpg", ".512.jpg")
        path = "/srv/flask/en4s/uploads"

        obj_id = ObjectId(unicode(complaint_id))

        db.metadata.update(
            {"type": "statistics"},
            {"$inc": {"complaint_count": -1}}
        )

        db.complaint.remove({"_id": obj_id})
        try:
            os.remove(path + picpath)
            os.remove(path + picpath512)
            # print db.complaint.find_one({"_id": obj_id})
            return {"success": "content deleted"}, 204
        except:
            return {"error": "something bad happened on delete"}, 404


class CommentsNew(restful.Resource):
    method_decorators = [authenticate]

    def put(self, complaint_id):
        data_dict = json.loads(request.data)
        user = session.get("user")

        obj_id = ObjectId(unicode(complaint_id))
        complaint_obj = db.complaint.find_one({"_id": obj_id})
        if not complaint_obj:
            return abort(404)

        comment_data = {}
        comment_data["_id"] = ObjectId()
        comment_data["date"] = datetime.now()
        comment_data["author"] = user["_id"]
        comment_data["text"] = data_dict["text"]
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


class CommentsVote(restful.Resource):
    method_decorators = [authenticate]

    def put(self, complaint_id):
        data_dict = json.loads(request.data)

        obj_id = ObjectId(unicode(complaint_id))
        complaint_obj = db.complaint.find_one({"_id": obj_id})
        if not complaint_obj:
            return abort(404)

        comment_id = data_dict["comment_id"]
        vote_type = data_dict["vote_type"]

        for comment in complaint_obj["comments"]:
            print comment["_id"]
            print comment_id
            if str(comment["_id"]) == str(comment_id):
                like_count = int(comment["like"])
                if vote_type == "upvote":
                    like_count += 1
                elif vote_type == "downvote":
                    like_count -= 1
                comment["like"] = like_count
                db.complaint.save(complaint_obj)
                return {"success": "upvote accepted"}, 202

        return abort(404)


class CommentsDelete(restful.Resource):
    method_decorators = [admin_authenticate]

    def post(self):
        data_dict = json.loads(request.data)
        obj_id = data_dict["complaint_id"]
        comment_id = data_dict["comment_id"]

        db.complaint.update(
            {"_id": ObjectId(obj_id)},
            {"$pull": {"comments": {"_id": ObjectId(comment_id)}}}
        )

        db.metadata.update(
            {"type": "statistics"},
            {"$inc": {"comment_count": -1}}
        )

        return 200


class Comments(restful.Resource):
    def get(self, complaint_id):
        obj_id = ObjectId(unicode(complaint_id))
        complaint_obj = db.complaint.find_one({"_id": obj_id})
        if not complaint_obj:
            return abort(404)

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

api.add_resource(Hatirlat, '/hatirlat')
api.add_resource(Login, '/login')
api.add_resource(Logout, '/logout')
api.add_resource(FacebookLogin, '/login/facebook')
api.add_resource(Register, '/register')
api.add_resource(Complaint, '/complaint')
api.add_resource(ComplaintDelete, '/complaint/delete')
api.add_resource(ComplaintSingle, '/complaint/<string:obj_id>')
api.add_resource(ComplaintSingleSlug, '/slug/<string:city>/<string:slug>')
api.add_resource(ComplaintUpvote, '/complaint/<string:obj_id>/upvote')
api.add_resource(ComplaintDownvote, '/complaint/<string:obj_id>/downvote')
api.add_resource(ComplaintRecent, '/complaint/recent')
api.add_resource(ComplaintHot, '/complaint/hot')
api.add_resource(ComplaintAll, '/complaint/all')
api.add_resource(ComplaintTop, '/complaint/top')
api.add_resource(ComplaintNear, '/complaint/near')
api.add_resource(ComplaintPicture, '/upload/<string:obj_id>')
api.add_resource(Comments, '/comments/<string:complaint_id>')
api.add_resource(CommentsNew, '/comments/<string:complaint_id>')
api.add_resource(CommentsVote, '/comments/vote/<string:complaint_id>')
api.add_resource(CommentsDelete, '/comments/delete')

if __name__ == '__main__':
    app.debug = settings.DEBUG
    app.secret_key = settings.SECRET
    app.run(host=settings.HOST, port=settings.PORT)
