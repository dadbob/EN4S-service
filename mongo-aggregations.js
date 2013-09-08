// returns the total vote count
db.complaint.aggregate([
    { "$group": {"_id": "", total_votes: {"$sum": "$upvote_count"}} },
    { "$project": {"_id": 0, total_votes: "$total_votes"} }]
)

// returns the total comment count
db.complaint.aggregate([
    { "$unwind": "$comments"},
    // todo
])
