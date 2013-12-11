from bson import json_util, ObjectId
from settings import db
from datetime import datetime

from serviceutils import make_slug
from serviceutils import serialize_mongodb_object


def note_single(city, slug):
    """

    Arguments:
    - `city`:
    """
    single_note = db.notes.find_one({"slug_url": "/not/" + city + "/" + slug})
    return serialize_mongodb_object(single_note)


def notes_for_city(city):
    """

    Arguments:
    - `city`:
    """
    notes = db.notes.find({"city": city})
    return json_util.dumps(notes)


def notes_to_city(session, city, district, note_title, note_description,
                  note_start_date, note_end_date, location,
                  source, fields, tags):

    """

    Arguments:
    - `city`:
    - `note_title`:
    - `note_full`:
    - `note_start_date`: if the note is a planned trouble
    - `note_end_date`: planned solution time
    - `location`: average location of the problem
    - `source`: source of the knowledge (izsu, aski etc)
    - `fields`: effected fields. Eg. (balgat mah, sogutozu etc)
    """

    sender = None
    if "gov" in session:
        sender = session.get("gov")["govname"]
        sender_city = session.get("gov")["city_slug"]
        if city != sender_city:
            return {"error": "not allowed to send notifications"}, 404
    elif "user" in session:
        if session.get("user")["user_type"] == "admin":
            sender = "enforce"
        else:
            return {"error": "not allowed to send notifications"}, 404

    if sender is None:
        return {"error": "sender is null, can't accept"}, 404

    slug_city = make_slug(city)
    slug_title = make_slug(note_title)

    number = db.metadata.find_one({"type": "statistics"})
    number = int(number["notification_count"])
    number += 1

    slug_url = "/not/" + slug_city + "/" + slug_title + "-" + str(number)

    start_date = datetime.strptime(
        note_start_date, "%d-%m-%Y %H:%M"
    )

    end_date = datetime.strptime(
        note_end_date, "%d-%m-%Y %H:%M"
    )

    fields = fields.split(",")
    new_fields = []
    for f in fields:
        new_fields.append(make_slug(f.strip()))

    tags = tags.split(",")
    new_tags = []
    for t in tags:
        new_tags.append(make_slug(t.strip()))

    new_note = {
        "_id": ObjectId(),
        "city": city,
        "slug_city": slug_city,
        "district": district,
        "slug_district": make_slug(district),
        "title": note_title,
        "description": note_description,
        "insert_date": datetime.now(),
        "start_date": start_date,
        "end_date": end_date,
        "sender": sender,
        "source": source,
        "location": location,
        "slug_url": slug_url,
        "areas": new_fields,
        "tags": new_tags
    }

    db.notes.insert(new_note)

    db.metadata.update(
        {"type": "statistics"},
        {"$inc": {"notification_count": 1}}
    )

    return json_util.dumps(new_note), 201
