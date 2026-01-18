import sys
import os
import tempfile
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

import bson
from bson import Binary, ObjectId
from flask import Flask, jsonify, request

from backend.mongo import connect

current_dir = os.path.dirname(os.path.abspath(__file__))
sophi_path = os.path.join(current_dir, "ai-util", "sophi")
if sophi_path not in sys.path:
    sys.path.insert(0, sophi_path)

try:
    from sophi_ai import SophiAIUtil, SessionParameters, ClassFile, GeneratedQuestion, ValidationResult, HintResponse
    from wolfram_checker import WolframAlphaChecker
except ImportError as e:
    print(f"Error importing AI modules: {e}")
    SophiAIUtil = None

server = Flask(__name__, static_folder="frontend/dist", static_url_path="")
mongo = connect()

ai_util = SophiAIUtil() if SophiAIUtil else None

@dataclass
class Question:
    content: str
    userAnswer: str
    aiAnswer: str
    wasUserCorrect: bool
    questionId: str # Added to track specific questions
    metadata: Dict[str, Any] # Added to store AI metadata (validation prompt, etc.)

@dataclass
class FileUpload:
    filename: str
    data: Binary

@dataclass
class Session:
    name: str
    classID: str
    adaptive: bool
    difficulty: float
    isCumulative : bool
    selectedTopics: List[str] #optional
    customRequests: str #optional
    file: FileUpload #optional

@dataclass
class Metric:
    rightAnswers: int
    totalAnswers: int

@dataclass
class Class:
    syllabus: FileUpload
    styleFiles: List[FileUpload] #optional
    name: str
    professor: str
    topics: List[str]
    metrics: Dict[str, Metric]
    sessions: List[Session]
    classFile: Optional[Dict[str, Any]] = None # To store processed ClassFile from AI

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

    syllabus_file_obj = FileUpload(
        filename=syllabus_file.filename,
        data=Binary(syllabus_bytes)
    )

    style_files = []
    for sf in request.files.getlist("styleFiles"):
        if sf and sf.filename:
            style_files.append(FileUpload(
                filename=sf.filename,
                data=Binary(sf.read())
            ))

    class_file_data = None
    extracted_topics = []

    if ai_util:
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_syllabus:
                tmp_syllabus.write(syllabus_bytes)
                tmp_syllabus_path = tmp_syllabus.name
            
            try:
                generated_class_file = ai_util.create_class_file_from_pdfs(
                    syllabus_pdf_path=tmp_syllabus_path,
                    problem_pdf_paths=[],
                    class_name=request.form.get("name", "Untitled Class")
                )
                
                class_file_data = generated_class_file.to_dict()
                extracted_topics = generated_class_file.concepts
                
            finally:
                if os.path.exists(tmp_syllabus_path):
                    os.remove(tmp_syllabus_path)
                    
        except Exception as e:
            print(f"Error generating class file: {e}")

    class_doc = Class(
        syllabus=syllabus_file_obj,
        styleFiles=style_files,
        name=request.form.get("name", "Untitled Class"),
        professor=request.form.get("professor", "Unknown"),
        topics=extracted_topics,
        sessions=[],
        classFile=class_file_data,
        metrics={}
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

    file_doc = FileUpload(
        filename=file_storage.filename if file_storage else "",
        data=file_bin
    )

    session = Session(
        name=request.form.get("name", "New Session"),
        classID=classID,
        adaptive=request.form.get("adaptive", "false").lower() == "true",
        difficulty=float(request.form.get("difficulty", 0.5)), # 0.0 to 1.0, map to 1-5 for AI
        isCumulative=request.form.get("cumulative", "false").lower() == "true",
        selectedTopics=request.form.getlist("selectedTopics"),
        customRequests=request.form.get("customRequests", ""),
        file=file_doc
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
    sessions = mongo.sessions.find(
        {"classID": classID},
        {"name": 1, "selectedTopics": 1}
    ).sort("_id", -1).limit(5)

    return jsonify([
        {
            "sessionID": str(doc["_id"]),
            "topics": doc.get("selectedTopics", []) or [],
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
        {
            "name": 1,
            "classID":1,
            "difficulty": 1,
            "isCumulative": 1,
            "adaptive": 1,
            "selectedTopics": 1,
            "customRequests": 1
        }
    )
    if not doc:
        return jsonify({"error": "Session not found"}), 404

    session = {
        "name": doc.get("name", "New Session"),
        "difficulty": doc.get("difficulty", 0.5),
        "classID": doc.get("classID", ""),
        "isCumulative": doc.get("isCumulative", False),
        "adaptive": doc.get("adaptive", True),
        "selectedTopics": doc.get("selectedTopics", []),
        "customRequests": doc.get("customRequests", "")
    }

    return jsonify(session)

@server.route("/api/requestQuestion/<sessionID>", methods=["GET"])
def request_question(sessionID):
    try:
        obj_id = ObjectId(sessionID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid sessionID"}), 400

    session_doc = mongo.sessions.find_one({"_id": obj_id})
    if not session_doc:
        return jsonify({"error": "Session not found"}), 404

    existing_pending = mongo.pending_questions.find_one({"sessionID": str(session_doc["_id"])})
    if existing_pending:
        return jsonify({
            "questionId": existing_pending.get("questionId"),
            "content": existing_pending.get("content")
        })

    if not ai_util:
        return jsonify({"error": "AI module not initialized"}), 500

    class_id_str = session_doc.get("classID")
    class_doc = None
    if class_id_str:
        try:
            class_doc = mongo.classes.find_one({"_id": ObjectId(class_id_str)})
        except:
            pass

    diff_float = float(session_doc.get("difficulty", 0.5))
    difficulty_level = max(1, min(5, int(diff_float * 5)))

    sess_params = SessionParameters(
        difficulty_level=difficulty_level,
        cumulative=session_doc.get("isCumulative", False),
        adaptive=session_doc.get("adaptive", True),
        focus_concepts=session_doc.get("selectedTopics", []),
        unit_focus=None
    )

    questions = session_doc.get("questions", [])
    history = []
    for q in questions:
        h_item = {
            "question": q.get("content"),
            "correct": q.get("wasUserCorrect"),
        }
        history.append(h_item)

    class_file_obj = None
    if class_doc and class_doc.get("classFile"):
        try:
            class_file_obj = ClassFile.from_dict(class_doc["classFile"])
        except:
            pass

    try:
        generated_q = ai_util.generate_question(
            session=sess_params,
            question_answer_history=history,
            class_file=class_file_obj,
            user_suggestions=session_doc.get("customRequests"),
            use_wolfram=True
        )
    except Exception as e:
        print(f"Error generating question: {e}")
        return jsonify({"error": f"Failed to generate question: {str(e)}"}), 500

    evaluated_topics = []
    if class_doc:
        class_topics = class_doc.get("topics", [])
        if class_topics:
            try:
                evaluated_topics = ai_util.evaluate_question_topics(
                    question=generated_q.question,
                    class_topics=class_topics
                )
            except Exception as e:
                print(f"Topic evaluation failed: {e}")

    q_id = str(ObjectId())

    pending_q = {
        "sessionID": str(session_doc["_id"]),
        "questionId": q_id,
        "content": generated_q.question,
        "aiAnswer": generated_q.answer,
        "wolfram_query": generated_q.wolfram_query,
        "validation_prompt": generated_q.validation_prompt,
        "metadata": generated_q.metadata,
        "topics": evaluated_topics,
    }
    mongo.pending_questions.insert_one(pending_q)

    return jsonify({
        "questionId": q_id,
        "content": generated_q.question,
        "topics": evaluated_topics
    })


@server.route("/api/submitAnswer/<questionID>", methods=["POST"])
def submit_answer(questionID):
    if not ai_util:
        return jsonify({"error": "AI module not initialized"}), 500

    pending = mongo.pending_questions.find_one({"questionId": questionID})
    if not pending:
        return jsonify({"error": "Question not found or expired"}), 404

    user_answer = request.json.get("answer") if request.is_json else request.form.get("answer")
    if not user_answer:
        return jsonify({"error": "No answer provided"}), 400

    validation_prompt = pending.get("validation_prompt")
    question_text = pending.get("content")

    is_correct = False

    system_instruction = validation_prompt or "You are a math tutor. Verify the student's answer."
    user_prompt = json.dumps({
        "question": question_text,
        "student_step_or_answer": user_answer,
        "output_contract": {
            "ok": "boolean",
            "feedback": "string"
        }
    }, ensure_ascii=False)

    question_topics = pending.get("topics", [])

    try:
        val_res = ai_util.gemini.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_prompt
        )
        is_correct = bool(val_res.get("ok"))
        feedback = str(val_res.get("feedback") or "")
    except Exception as e:
        print(f"Validation failed: {e}")
        feedback = "Could not verify answer automatically."

    session_doc = mongo.sessions.find_one({"_id": ObjectId(pending["sessionID"])})
    if session_doc:
        class_id_str = session_doc.get("classID")
        if class_id_str:
            class_doc = mongo.classes.find_one({"_id": ObjectId(class_id_str)})
            if class_doc:
                metrics = class_doc.get("metrics", {})
                for topic in question_topics:
                    if topic:
                        if topic not in metrics:
                            metrics[topic] = asdict(Metric(rightAnswers=0, totalAnswers=0))
                        metric_entry = metrics[topic]
                        metric_entry["totalAnswers"] += 1
                        if is_correct:
                            metric_entry["rightAnswers"] += 1
                        metrics[topic] = metric_entry
                mongo.classes.update_one(
                    {"_id": ObjectId(class_id_str)},
                    {"$set": {"metrics": metrics}}
                )

    question_entry = Question(
        content=question_text,
        userAnswer=user_answer,
        aiAnswer=pending.get("aiAnswer"),
        wasUserCorrect=is_correct,
        questionId=questionID,
        metadata=pending.get("metadata", {})
    )

    mongo.sessions.update_one(
        {"_id": ObjectId(pending["sessionID"])},
        {"$push": {"questions": asdict(question_entry)}}
    )

    # Cleanup pending? (Optional, keep for logs)
    mongo.pending_questions.delete_one({"questionId": questionID})

    return jsonify({
        "isCorrect": is_correct,
        "correctAnswer": pending.get("aiAnswer"),
        "whyIsWrong": feedback if not is_correct else "Correct!"
    })

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
    if "selectedTopics" in request.form:
        update_fields["selectedTopics"] = request.form.getlist("selectedTopics")
    if "customRequests" in request.form:
        update_fields["customRequests"] = request.form["customRequests"]

    if not update_fields:
        return jsonify({"error": "No valid fields to update"}), 400

    result = mongo.sessions.update_one(
        {"_id": obj_id},
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"status": "Session parameters updated"})

@server.route("/api/setAdaptive/<sessionID>", methods=["POST"])
def set_adaptive(sessionID):
    try:
        obj_id = ObjectId(sessionID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid sessionID"}), 400

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
        return jsonify({"error": "No adaptive setting provided"}), 400

    result = mongo.sessions.update_one(
        {"_id": obj_id},
        {"$set": {"adaptive": adaptive}}
    )
    if result.matched_count == 0:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"status": "Adaptive setting updated"})

@server.route("/api/requestHint/<questionID>", methods=["GET", "POST"])
def request_hint(questionID):
    if not ai_util:
        return jsonify({"error": "AI module not initialized"}), 500

    pending = mongo.pending_questions.find_one({"questionId": questionID})
    if not pending:
        return jsonify({"error": "Question not found"}), 404

    question_text = pending.get("content")
    
    existing_hints_data = pending.get("hints", [])
    hint_history = [h.get("text", "") for h in existing_hints_data if h.get("text")]

    image_file = None
    image_bytes = None
    if "photo" in request.files:
        image_file = request.files["photo"]
        image_bytes = image_file.read()

    status_prompt = (
        request.form.get("hintRequest")
        or request.args.get("status")
        or request.form.get("status")
        or "I am stuck and unsure what to do next."
    )
    
    req_hint_type = "Strategic" if not hint_history else None

    try:
        hint_res = ai_util.generate_hint(
            status_prompt=status_prompt,
            problem=question_text,
            hint_history=hint_history,
            hint_type=req_hint_type,
            use_wolfram=True,
            status_image=image_bytes if "photo" in request.files else None,
            status_image_mime_type=image_file.mimetype if image_file else None
        )

        new_hint_entry = {
            "text": hint_res.text,
            "kind": hint_res.kind,
            "hint_type": hint_res.hint_type,
            "wolfram_query": hint_res.wolfram_query,
            "timestamp": bson.datetime.datetime.now()
        }
        mongo.pending_questions.update_one(
            {"questionId": questionID},
            {"$push": {"hints": new_hint_entry}}
        )

        return jsonify({
            "hint": hint_res.text,
            "kind": hint_res.kind,
            "hint_type": hint_res.hint_type
        })
    except Exception as e:
        print(f"Hint generation failed: {e}")
        return jsonify({"hint": "Try breaking the problem into smaller steps."})

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

    syllabus_file_obj = FileUpload(
        filename=syllabus_file.filename,
        data=Binary(syllabus_bytes)
    )

    result = mongo.classes.update_one(
        {"_id": obj_id},
        {"$set": {"syllabus": asdict(syllabus_file_obj)}}
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
            style_files.append(FileUpload(
                filename=sf.filename,
                data=Binary(sf.read())
            ))
    if not style_files:
        return jsonify({"error": "No style files provided"}), 400
    result = mongo.classes.update_one(
        {"_id": obj_id},
        {"$push": {"styleFiles": {"$each": [asdict(sf) for sf in style_files]}}}
    )
    if result.matched_count == 0:
        return jsonify({"error": "Class not found"}), 404
    return jsonify({"status": "Style docs uploaded"})

@server.route("/api/deleteStyleDoc/<classID>/<docName>", methods=["DELETE"])
def delete_style_doc(classID, docName):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    result = mongo.classes.update_one(
        {"_id": obj_id},
        {"$pull": {"styleFiles": {"filename": docName}}}
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
    return jsonify([
        {
            "filename": sf.get("filename", ""),
        }
        for sf in style_files
    ])

@server.route("/api/getMetrics/<classID>", methods=["GET"])
def get_metrics(classID):
    try:
        obj_id = ObjectId(classID)
    except bson.errors.InvalidId:
        return jsonify({"error": "Invalid classID"}), 400

    doc = mongo.classes.find_one({"_id": obj_id}, {"metrics": 1})
    if not doc:
        return jsonify({"error": "Class not found"}), 404
    metrics = doc.get("metrics", {})
    return jsonify(metrics)


@server.route("/", defaults={"path": ""})
@server.route("/<path:path>")
def spa(path):
    if path.startswith("api"):
        return jsonify({"error": "API route not found"}), 404

    return server.send_static_file("index.html")

if __name__ == '__main__':
    server.run(port=8080)
