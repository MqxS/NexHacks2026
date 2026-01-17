from flask import Flask, jsonify

server = Flask(__name__, static_folder="frontend/dist", static_url_path="")

@server.route("/api/hello")
def hello():
    return jsonify({"message": "API Working!"})

@server.route("/api/getClassCards")
def get_class_cards():
    class_cards = [
        {"id": 1, "name": "Mathematics", "professor": "Dr. Karthik"},
        {"id": 2, "name": "Science", "professor": "Dr. Joseph"},
        {"id": 3, "name": "History", "professor": "Dr. Max"}
    ]
    return jsonify(class_cards)

@server.route("/api/getClass")
def crease_class():
    classes = [
        {"id": 1}
    ]
    return jsonify(classes)

@server.route("/api/createSession")
def create_session():
    session = {
        "sessionID": "ABC123",
    }
    return jsonify(session)

@server.route("/api/getClassTopics/<classID>")
def get_class_topics(classID):
    topics = [
        {"title": "Algebra"},
        {"title": "Geometry"},
        {"title": "Calculus"}
    ]
    return jsonify(topics)

@server.route("/api/requestQuestion/<sessionID>")
def request_question(sessionID):
    question = {
        "questionId": "Q123",
        "content": "What is the capital of France?"
    }
    return jsonify(question)

@server.route("/api/submitAnswer/<questionID>", methods=["POST"])
def submit_answer(questionID):
    response = {
        "isCorrect": True,
        "correctAnswer": "Paris",
        "whyIsWrong": "Paris is the capital and most populous city of France.",
    }
    return jsonify(response)

@server.route("/api/updateSessionParams/<sessionID>", methods=["POST"])
def update_session_params(sessionID):
    return jsonify({"status": "Session parameters updated"})

@server.route("/api/setAdaptive/<sessionID>", methods=["POST"])
def set_adaptive(sessionID):
    return jsonify({"status": "Adaptive learning set"})

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
