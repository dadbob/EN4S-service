from bson import json_util, ObjectId
from settings import db
from datetime import datetime


def notes_for_city(city):
    """

    Arguments:
    - `city`:
    """
    notes = db.notes.find({"city": city})
    return json_util.dumps(notes)


def notes_to_city(session, city, note_title, note_full):
    """

    Arguments:
    - `city`:
    - `note_title`:
    - `note_full`:
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

    new_note = {
        "_id": ObjectId(),
        "note_city": city,
        "note_title": note_title,
        "note_full": note_full,
        "note_date": datetime.now(),
        "note_sender": sender
    }

    db.notes.insert(new_note)

    return json_util.dumps(new_note)
