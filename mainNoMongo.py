import json
import random
import time
from dataclasses import dataclass
from typing import List

from bson import ObjectId, Binary
from flask import Flask, jsonify, request

server = Flask(__name__, static_folder="frontend/dist", static_url_path="")

@dataclass
class Question:
    questionId: ObjectId
    content: str
    userAnswer: str
    aiAnswer: str
    wasUserCorrect: bool

@dataclass
class Session:
    sessionID: ObjectId
    name: str
    questions: List[Question]
    adaptive: bool
    difficulty: float
    isCumulative : bool
    focusedConcepts: List[str]
    file: Binary

@dataclass
class Class:
    classID: ObjectId
    syllabus: Binary
    styleFiles: List[Binary]
    name: str
    professor: str
    topics: List[str]
    sessions: List[Session]

class_cards = [
    {"classID": 1, "name": "Mathematics", "professor": "Dr. Karthik"},
    {"classID": 2, "name": "Science", "professor": "Dr. Joseph"},
    {"classID": 3, "name": "History", "professor": "Dr. Max"}
]

sessions_store = {}

@server.route("/api/hello")
def hello():
    return jsonify({"message": "API Working!"})

@server.route("/api/getClassCards")
def get_class_cards():
    return jsonify(class_cards)

@server.route("/api/createClass", methods=["POST"])
def create_class():
    time.sleep(1.5)
    payload = request.get_json(silent=True) or {}
    name = (
        request.form.get("Name")
        or request.form.get("name")
        or payload.get("Name")
        or payload.get("name")
        or "Untitled class"
    )
    professor = (
        request.form.get("Professor")
        or request.form.get("professor")
        or payload.get("Professor")
        or payload.get("professor")
        or "Instructor"
    )
    next_id = max(card["classID"] for card in class_cards) + 1 if class_cards else 1
    class_cards.append({"classID": next_id, "name": name, "professor": professor})
    return jsonify({"classID": str(next_id)})

@server.route("/api/createSession/<classID>", methods=["POST"])
def create_session(classID):
    time.sleep(1.2)
    payload = request.get_json(silent=True) or {}
    name = request.form.get("name") or payload.get("name") or "New Session"
    difficulty = request.form.get("difficulty") or payload.get("difficulty") or 0.5
    adaptive = request.form.get("adaptive") or payload.get("adaptive") or False
    cumulative = request.form.get("cumulative") or payload.get("cumulative") or False
    custom_requests = request.form.get("customRequests") or payload.get("customRequests") or ""

    selected_topics = request.form.getlist("selectedTopics")
    if not selected_topics:
        raw_topics = payload.get("selectedTopics") or request.form.get("selectedTopics") or payload.get("topics")
        if isinstance(raw_topics, str):
            try:
                parsed = json.loads(raw_topics)
                if isinstance(parsed, list):
                    selected_topics = parsed
                elif parsed:
                    selected_topics = [str(parsed)]
            except json.JSONDecodeError:
                selected_topics = [raw_topics]
        elif isinstance(raw_topics, list):
            selected_topics = raw_topics

    session_id = f"S{random.randint(1000, 9999)}"
    sessions_store[session_id] = {
        "name": name,
        "difficulty": float(difficulty),
        "classID": classID,
        "isCumulative": str(cumulative).lower() == "true",
        "adaptive": str(adaptive).lower() == "true",
        "selectedTopics": selected_topics,
        "customRequests": custom_requests
    }
    return jsonify({"sessionID": session_id})

@server.route("/api/replaceSyllabus/<classID>", methods=["POST"])
def replace_syllabus(classID):
    time.sleep(1.2)
    return jsonify({"status": "Syllabus replaced"})

@server.route("/api/uploadStyleDocs/<classID>", methods=["POST"])
def upload_style_docs(classID):
    time.sleep(1.4)
    return jsonify({"status": "Style docs uploaded"})

@server.route("/api/deleteStyleDoc/<classID>/<docName>", methods=["DELETE"])
def delete_style_doc(classID, docName):
    time.sleep(0.8)
    return jsonify({"status": "Style doc deleted"})

@server.route("/api/getStyleDocs/<classID>", methods=["GET"])
def get_style_docs(classID):
    time.sleep(0.4)
    return jsonify([
        {"filename": "lecture-notes.pdf"},
        {"filename": "style-guide.md"}
    ])

@server.route("/api/getClassTopics/<classID>")
def get_class_topics(classID):
    topics = [
        {"title": "Algebra"},
        {"title": "Geometry"},
        {"title": "Calculus"}
    ]
    return jsonify(topics)

@server.route("/api/getRecentSessions/<classID>")
def get_recent_sessions(classID):
    sessions = [
        {
            "sessionID": "S1",
            "name": "Test Session 1",
            # "timestamp": "2026-01-17T14:10:00Z",
            "topics": ["Algebra", "Geometry"]
        },
        {
            "sessionID": "S2",
            "name": "Test Session 2",
            # "timestamp": "2026-01-16T18:30:00Z",
            "topics": ["Calculus"]
        }
    ]
    return jsonify(sessions)

@server.route("/api/getSessionParams/<sessionID>")
def get_session_params(sessionID):
    session_params = sessions_store.get(sessionID)
    if session_params:
        return jsonify(session_params)
    return jsonify({
        "name": "Midterm review",
        "difficulty": 0.6,
        "classID": "",
        "isCumulative": False,
        "adaptive": True,
        "selectedTopics": ["Algebra"],
        "customRequests": ""
    })

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

@server.route("/api/setAdaptive/<sessionID>", methods=["POST"])
def set_adaptive(sessionID):
    payload = request.get_json(silent=True) or {}
    if "active" in payload:
        adaptive = bool(payload.get("active"))
    elif "adaptive" in payload:
        adaptive = bool(payload.get("adaptive"))
    elif "active" in request.form:
        adaptive = request.form.get("active").lower() == "true"
    elif "adaptive" in request.form:
        adaptive = request.form.get("adaptive").lower() == "true"
    else:
        adaptive = False

    if sessionID in sessions_store:
        sessions_store[sessionID]["adaptive"] = adaptive
    return jsonify({"status": "Adaptive learning set"})

@server.route("/api/setAdaptive/<sessionID>/<setting>", methods=["POST"])
def set_adaptive_legacy(sessionID, setting):
    adaptive = setting.lower() == "true"
    if sessionID in sessions_store:
        sessions_store[sessionID]["adaptive"] = adaptive
    return jsonify({"status": "Adaptive learning set"})

@server.route("/api/requestHint/<questionID>")
def request_hint(questionID):
    hint = {
        "hint": "It's also known as the city of lights."
    }
    return jsonify(hint)

@server.route("/api/editClassName/<classID>", methods=["POST"])
def edit_class_name(classID):
    try:
        class_id = int(classID)
    except ValueError:
        return jsonify({"error": "Invalid classID"}), 400

    new_name = request.form.get("name")
    if not new_name:
        return jsonify({"error": "No name provided"}), 400

    for card in class_cards:
        if card["classID"] == class_id:
            card["name"] = new_name
            return jsonify({"status": "Class name updated"})

    return jsonify({"error": "Class not found"}), 404

@server.route("/api/editClassProf/<classID>", methods=["POST"])
def edit_class_prof(classID):
    try:
        class_id = int(classID)
    except ValueError:
        return jsonify({"error": "Invalid classID"}), 400

    new_professor = request.form.get("professor")
    if not new_professor:
        return jsonify({"error": "No professor name provided"}), 400

    for card in class_cards:
        if card["classID"] == class_id:
            card["professor"] = new_professor
            return jsonify({"status": "Class professor updated"})

    return jsonify({"error": "Class not found"}), 404

@server.route("/api/deleteClass/<classID>", methods=["DELETE", "POST"])
def delete_class(classID):
    try:
        class_id = int(classID)
    except ValueError:
        return jsonify({"error": "Invalid classID"}), 400

    for index, card in enumerate(class_cards):
        if card["classID"] == class_id:
            class_cards.pop(index)
            return jsonify({"status": "Class deleted"})

    return jsonify({"error": "Class not found"}), 404

@server.route("/api/deleteSession/<sessionID>", methods=["DELETE"])
def delete_session(sessionID):
    if sessionID in sessions_store:
        sessions_store.pop(sessionID, None)
        return jsonify({"status": "Session deleted"})
    return jsonify({"error": "Session not found"}), 404

@server.route("/", defaults={"path": ""})
@server.route("/<path:path>")
def spa(path):
    if path.startswith("api"):
        return jsonify({"error": "API route not found"}), 404

    return server.send_static_file("index.html")

if __name__ == '__main__':
    server.run(port=8080)
