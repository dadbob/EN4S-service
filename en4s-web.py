from flask import Flask
from flask import render_template, redirect, request

from settings import db
import settings
import pymongo
# from bson import ObjectId

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/betalogin', methods=['POST'])
def betalogin():
    betapass = request.form['beta']

    if betapass == settings.BETAPASS:
        print "pass ok"
    else:
        print "invalid login"

    return redirect('/')


@app.route('/dashboard')
def dashboard():
    items = db.complaint.find({"city": "Ankara"})
    items = items.sort("upvote_count", pymongo.DESCENDING)
    items.limit(10)
    return render_template('dashboard.html', items=items)


if __name__ == '__main__':
    app.debug = settings.DEBUG
    app.secret_key = settings.SECRET
    app.run(host=settings.HOST, port=settings.PORT + 1)
