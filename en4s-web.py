from flask import Flask, session
from flask import render_template, redirect, request
from flask.ext import restful

from settings import db
import settings
import pymongo
# from bson import ObjectId

app = Flask(__name__)
api = restful.Api(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/betalogin', methods=['POST'])
def betalogin():
    betapass = request.form['beta']

    if betapass == settings.BETAPASS:
        session['logged_in'] = True
        return redirect('/home')
    else:
        print "invalid login"

    return redirect('/')


@app.route('/home')
def home():
    if session.get('logged_in'):
        items = db.complaint.find()
        items = items.sort("date", pymongo.DESCENDING)
        items.limit(15)
        # for item in items:
        #     print type(item["upvote_count"])

        return render_template('home/index.html', items=items)
    else:
        return redirect('/')


class ComplaintNear(restful.Resource):
    def get(self):
        l = []

        lati = request.args.get('latitude', '')
        longi = request.args.get('longitude', '')
        category = request.args.get('category', '')
        print "latitude: " + unicode(lati)
        print "longitude: " + unicode(longi)

        if category is "":
            category = "all"

        loc = [float(lati), float(longi)]
        if category is not 'all':
            items = db.complaint.find({"category": category,
                                       "location": {"$near": loc}})
        else:
            items = db.complaint.find({"location": {"$near": loc}})

        items = items[:10]      # limit 10 item

        for item in items:
            item["_id"] = unicode(item["_id"])
            item["date"] = unicode(
                item["date"].strftime("%Y-%m-%d %H:%M:%S.%f"))
            l.append(item)

        return (l, 200, {"Cache-Control": "no-cache"})


@app.route('/dashboard')
def dashboard():
    items = db.complaint.find({"city": "Ankara"})
    items = items.sort("upvote_count", pymongo.DESCENDING)
    items.limit(10)
    return render_template('dashboard.html', items=items)

api.add_resource(ComplaintNear, '/complaint/near')

if __name__ == '__main__':
    app.debug = settings.DEBUG
    app.secret_key = settings.SECRET
    app.run(host=settings.HOST, port=settings.PORT + 1)