import random
from dataclasses import dataclass, asdict
from typing import List

import bson
from bson import Binary, ObjectId
from flask import Flask, jsonify, request

from backend.mongo import connect

server = Flask(__name__, static_folder="frontend/dist", static_url_path="")
mongo = connect()

@dataclass
class Question:
    content: str
    userAnswer: str
    aiAnswer: str
    wasUserCorrect: bool

@dataclass
class Session:
    name: str
    classID: str
    questions: List[Question]
    adaptive: bool
    difficulty: float
    isCumulative : bool
    focusedConcepts: List[str] #optional
    file: Binary #optional

@dataclass
class Class:
    syllabus: Binary
    styleFiles: List[Binary] #optional
    name: str
    professor: str
    topics: List[str]
    sessions: List[Session]

@server.route("/api/hello")
def hello():
    return jsonify({"message": "API Working!"})

@server.route("/api/getClassCards", methods=["GET"])
def get_class_cards():
    classes = mongo.classes.find(
        {},
        {"name": 1, "professor": 1}
    )

    return jsonify([
        {
            "classID": str(doc["_id"]),
            "name": doc.get("name", "Untitled Class"),
            "professor": doc.get("professor", "Unknown")
        }
        for doc in classes
        if "_id" in doc
    ])

@server.route("/api/createClass", methods=["POST"])
def create_class():
    #multipart/form-data
    if "syllabus" not in request.files:
        return jsonify({"error": "No syllabus file provided"}), 400

    syllabus_file = request.files["syllabus"]
    syllabus_bytes = syllabus_file.read()

    style_files = []
    for sf in request.files.getlist("styleFiles"):
        if sf and sf.filename:
            style_files.append(Binary(sf.read()))

    class_doc = Class(
        syllabus=Binary(syllabus_bytes),
        styleFiles=style_files,
        name=request.form.get("name", "Untitled Class"),
        professor=request.form.get("professor", "Unknown"),
        topics=[],
        sessions=[]
    )

    result = mongo.classes.insert_one(asdict(class_doc))

    return jsonify({
        "classID": str(result.inserted_id)
    })

@server.route("/api/createSession/<classID>", methods=["POST"])
def create_session(classID):
    file_storage = request.files.get("file")
    if file_storage and file_storage.filename:
        file_bin = Binary(file_storage.read())
    else:
        file_bin = None

    session = Session(
        name=request.form.get("name", "New Session"),
        questions=[],
        classID=classID,
        adaptive=request.form.get("adaptive", "false").lower() == "true",
        difficulty=float(request.form.get("difficulty", 0.5)),
        isCumulative=request.form.get("cumulative", "false").lower() == "true",
        focusedConcepts=[],
        file=file_bin
    )

    result = mongo.sessions.insert_one(asdict(session))

    return jsonify({
        "sessionID": str(result.inserted_id)
    })

@server.route("/api/getClassTopics/<classID>", methods=["GET"])
def get_class_topics(classID):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    doc = mongo.classes.find_one({"_id": obj_id}, {"topics": 1})
    if not doc:
        return jsonify({"error": "Class not found"}), 404

    topics = doc.get("topics", [])
    if topics and all(isinstance(t, str) for t in topics):
        topics_out = [{"title": t} for t in topics]
    else:
        topics_out = topics

    return jsonify(topics_out)

@server.route("/api/getRecentSessions/<classID>", methods=["GET"])
def get_recent_sessions(classID):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    sessions = mongo.sessions.find(
        {"classID": obj_id},
        {"name": 1, "focusedConcepts": 1}
    ).sort("_id", -1).limit(5)

    return jsonify([
        {
            "sessionID": str(doc["_id"]),
            # "timestamp": doc["_id"].generation_time.isoformat(),
            "topics": doc.get("focusedConcepts", []) or [],
            "name": doc.get("name", "Untitled Session")
        }
        for doc in sessions
        if "_id" in doc
    ])

@server.route("/api/getSessionParams/<sessionID>", methods=["GET"])
def get_session_params(sessionID):
    try:
        obj_id = ObjectId(sessionID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid sessionID"}), 400

    doc = mongo.sessions.find_one(
        {"_id": obj_id},
        {"name": 1, "classID":1, "difficulty": 1, "isCumulative": 1, "adaptive": 1, "focusedConcepts": 1}
    )
    if not doc:
        return jsonify({"error": "Session not found"}), 404
    session = Session(
        name=doc.get("name", "New Session"),
        difficulty=doc.get("difficulty", 0.5),
        classID=doc.get("classID"),
        isCumulative=doc.get("isCumulative", False),
        adaptive=doc.get("adaptive", True),
        focusedConcepts=doc.get("focusedConcepts", []),
        questions=[],
        file=Binary(b"")
    )

    return jsonify(asdict(session))

#TODO: KARTHIK #1
@server.route("/api/requestQuestion/<sessionID>", methods=["GET"])
def request_question(sessionID):
    questions = [
        {"questionId": "Q101", "content": "What is the capital of France?"},
        {"questionId": "Q102", "content": "Solve for x: 2x + 5 = 17."},
        {"questionId": "Q103", "content": "Compute the derivative of $f(x)=x^2$."},
        {"questionId": "Q104", "content": "Evaluate the integral $\\int_0^1 3x^2\\,dx$."},
        {"questionId": "Q105", "content": "If $a^2+b^2=c^2$ with $a=3$ and $b=4$, find $c$."},
        {"questionId": "Q106", "content": "Simplify: $\\frac{2}{x} + \\frac{3}{x} = ?$"},
        {"questionId": "Q107", "content": "What is the slope of the line through $(1,2)$ and $(3,6)$?"},
        {"questionId": "Q108", "content": "Convert $0.75$ to a fraction."},
        {"questionId": "Q109", "content": "Solve: $\\sin(\\pi/2)$ = ?"},
        {"questionId": "Q110", "content": "Find the area of a circle with radius $r$."}
    ]
    return jsonify(random.choice(questions))

#TODO: KARTHIK #2
@server.route("/api/submitAnswer/<questionID>", methods=["POST"])
def submit_answer(questionID):
    feedback_bank = [
        {
            "isCorrect": True,
            "correctAnswer": "Paris",
            "whyIsWrong": ""
        },
        {
            "isCorrect": True,
            "correctAnswer": "$x=6$",
            "whyIsWrong": ""
        },
        {
            "isCorrect": True,
            "correctAnswer": "$f'(x)=2x$",
            "whyIsWrong": ""
        },
        {
            "isCorrect": False,
            "correctAnswer": "$x=6$",
            "whyIsWrong": "Isolate $x$ by subtracting 5 first, then divide by 2."
        },
        {
            "isCorrect": False,
            "correctAnswer": "$\\int_0^1 3x^2\\,dx = 1$",
            "whyIsWrong": "Use the antiderivative $x^3$ and evaluate from 0 to 1."
        },
        {
            "isCorrect": False,
            "correctAnswer": "$c=5$",
            "whyIsWrong": "Apply the Pythagorean theorem: $3^2+4^2=9+16=25$."
        },
        {
            "isCorrect": False,
            "correctAnswer": "$\\sin(\\pi/2)=1$",
            "whyIsWrong": "On the unit circle, $\\pi/2$ corresponds to the point $(0,1)$."
        }
    ]
    return jsonify(random.choice(feedback_bank))

@server.route("/api/updateSessionParams/<sessionID>", methods=["POST"])
def update_session_params(sessionID):
    try:
        obj_id = ObjectId(sessionID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid sessionID"}), 400

    update_fields = {}
    if "name" in request.form:
        update_fields["name"] = request.form["name"]
    if "difficulty" in request.form:
        try:
            update_fields["difficulty"] = float(request.form["difficulty"])
        except ValueError:
            return jsonify({"error": "Invalid difficulty value"}), 400
    if "cumulative" in request.form:
        update_fields["isCumulative"] = request.form["cumulative"].lower() == "true"
    if "focusedConcepts" in request.form:
        concepts = request.form.getlist("focusedConcepts")
        update_fields["focusedConcepts"] = concepts

    if not update_fields:
        return jsonify({"error": "No valid fields to update"}), 400

    result = mongo.sessions.update_one(
        {"_id": obj_id},
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"status": "Session parameters updated"})

@server.route("/api/setAdaptive/<sessionID>/<setting>", methods=["POST"])
def set_adaptive(sessionID, setting):
    try:
        obj_id = ObjectId(sessionID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid sessionID"}), 400

    adaptive = setting.lower() == "true"

    result = mongo.sessions.update_one(
        {"_id": obj_id},
        {"$set": {"adaptive": adaptive}}
    )
    if result.matched_count == 0:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"status": "Adaptive setting updated"})

#TODO: KARTHIK #3
@server.route("/api/requestHint/<questionID>")
def request_hint(questionID):
    hint = {
        "hint": "It's also known as the city of lights."
    }
    return jsonify(hint)

@server.route("/api/editClassName/<classID>", methods=["POST"])
def edit_class_name(classID):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    if "name" not in request.form:
        return jsonify({"error": "No name provided"}), 400

    new_name = request.form["name"]

    result = mongo.classes.update_one(
        {"_id": obj_id},
        {"$set": {"name": new_name}}
    )
    if result.matched_count == 0:
        return jsonify({"error": "Class not found"}), 404
    return jsonify({"status": "Class name updated"})

@server.route("/api/editClassProf/<classID>", methods=["POST"])
def edit_class_prof(classID):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    if "professor" not in request.form:
        return jsonify({"error": "No professor name provided"}), 400

    new_professor = request.form["professor"]

    result = mongo.classes.update_one(
        {"_id": obj_id},
        {"$set": {"professor": new_professor}}
    )
    if result.matched_count == 0:
        return jsonify({"error": "Class not found"}), 404
    return jsonify({"status": "Class professor updated"})

@server.route("/api/deleteClass/<classID>", methods=["DELETE", "POST"])
def delete_class(classID):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    result = mongo.classes.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Class not found"}), 404
    return jsonify({"status": "Class deleted"})


@server.route("/api/deleteSession/<sessionID>", methods=["DELETE"])
def delete_session(sessionID):
    try:
        obj_id = ObjectId(sessionID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid sessionID"}), 400

    result = mongo.sessions.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"status": "Session deleted"})

@server.route("/api/replaceSyllabus/<classID>", methods=["POST"])
def replace_syllabus(classID):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    if "syllabus" not in request.files:
        return jsonify({"error": "No syllabus file provided"}), 400

    syllabus_file = request.files["syllabus"]
    syllabus_bytes = syllabus_file.read()

    result = mongo.classes.update_one(
        {"_id": obj_id},
        {"$set": {"syllabus": Binary(syllabus_bytes)}}
    )
    if result.matched_count == 0:
        return jsonify({"error": "Class not found"}), 404
    return jsonify({"status": "Syllabus replaced"})

@server.route("/api/uploadStyleDocs/<classID>", methods=["POST"])
def upload_style_docs(classID):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    style_files = []
    for sf in request.files.getlist("styleFiles"):
        if sf and sf.filename:
            style_files.append(Binary(sf.read()))

    if not style_files:
        return jsonify({"error": "No style files provided"}), 400

    result = mongo.classes.update_one(
        {"_id": obj_id},
        {"$push": {"styleFiles": {"$each": style_files}}}
    )
    if result.matched_count == 0:
        return jsonify({"error": "Class not found"}), 404
    return jsonify({"status": "Style documents uploaded"})

@server.route("/api/deleteStyleDoc/<classID>", methods=["DELETE"])
def delete_style_doc(classID):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    result = mongo.classes.update_one(
        {"_id": obj_id},
        {"$pull": {"styleFiles": request.args.get("docID", "")}}
    )
    if result.matched_count == 0:
        return jsonify({"error": "Class not found"}), 404
    return jsonify({"status": "Style doc deleted"})

@server.route("/api/getStyleDocs/<classID>", methods=["GET"])
def get_style_docs(classID):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    doc = mongo.classes.find_one({"_id": obj_id}, {"styleFiles": 1})
    if not doc:
        return jsonify({"error": "Class not found"}), 404
    style_files = doc.get("styleFiles", [])
    files_data = [sf.decode('utf-8', errors='ignore') for sf in style_files]
    return jsonify({"styleFiles": files_data})

@server.route("/", defaults={"path": ""})
@server.route("/<path:path>")
def spa(path):
    if path.startswith("api"):
        return jsonify({"error": "API route not found"}), 404

    return server.send_static_file("index.html")

if __name__ == '__main__':
    server.run(port=8080)
