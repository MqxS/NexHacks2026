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

@server.route("/api/createSession/<classID>")
def create_session(classID):
    file_storage = request.files.get("file")
    if file_storage and file_storage.filename:
        file_bin = Binary(file_storage.read())
    else:
        file_bin = None

    session = Session(
        name=request.form.get("name", "New Session"),
        questions=[],
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

@server.route("/api/getClassTopics/<classID>")
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

@server.route("/api/getRecentSessions/<classID>")
def get_recent_sessions(classID):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    sessions = mongo.sessions.find(
        {"classID": obj_id},
        {"name": 1}
    ).sort("_id", -1).limit(5)

    return jsonify([
        {
            "sessionID": str(doc["_id"]),
            "name": doc.get("name", "Untitled Session")
        }
        for doc in sessions
        if "_id" in doc
    ])

@server.route("/api/getSessionParams/<sessionID>")
def get_session_params(sessionID):
    try:
        obj_id = ObjectId(sessionID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid sessionID"}), 400

    doc = mongo.sessions.find_one(
        {"_id": obj_id},
        {"name": 1, "difficulty": 1, "isCumulative": 1, "adaptive": 1, "focusedConcepts": 1}
    )
    if not doc:
        return jsonify({"error": "Session not found"}), 404
    session = Session(
        name=request.form.get("name", "New Session"),
        difficulty=doc.get("difficulty", 0.5),
        isCumulative=doc.get("isCumulative", False),
        adaptive=doc.get("adaptive", True),
        focusedConcepts=doc.get("focusedConcepts", []),
        questions=[],
        file=Binary(b"")
    )

    return jsonify(asdict(session))

#TODO: KARTHIK #1
@server.route("/api/requestQuestion/<sessionID>")
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

@server.route("/", defaults={"path": ""})
@server.route("/<path:path>")
def spa(path):
    if path.startswith("api"):
        return jsonify({"error": "API route not found"}), 404

    return server.send_static_file("index.html")

if __name__ == '__main__':
    server.run(port=8080)
