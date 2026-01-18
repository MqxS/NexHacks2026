import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json
from bson import ObjectId

# Mocking modules before importing main_ai
sys.modules["backend.mongo"] = MagicMock()
sys.modules["sophi_ai"] = MagicMock()
sys.modules["wolfram_checker"] = MagicMock()

# Add the project root to sys.path so we can import main_ai
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Now import main_ai
import main

class TestMainAI(unittest.TestCase):
    def setUp(self):
        self.app = main.server.test_client()
        self.app.testing = True
        
        # Mock Mongo
        self.mock_mongo = main.mongo
        self.mock_sessions = self.mock_mongo.sessions
        self.mock_classes = self.mock_mongo.classes
        self.mock_pending = self.mock_mongo.pending_questions
        
        # Mock AI Util
        self.mock_ai = main.ai_util
        if self.mock_ai is None:
            # If main failed to init AI (e.g. import error), we force mock it
            main.ai_util = MagicMock()
            self.mock_ai = main.ai_util

    def test_request_question(self):
        session_id = str(ObjectId())
        
        # Setup mock session return
        self.mock_sessions.find_one.return_value = {
            "_id": ObjectId(session_id),
            "difficulty": 0.6,
            "isCumulative": False,
            "adaptive": True,
            "selectedTopics": ["algebra"],
            "questions": []
        }
        
        # Setup mock AI generation
        mock_q = MagicMock()
        mock_q.question = "Solve x+1=2"
        mock_q.answer = "x=1"
        mock_q.wolfram_query = "Solve x+1=2"
        mock_q.validation_prompt = "Validate this."
        mock_q.metadata = {}
        self.mock_ai.generate_question.return_value = mock_q
        
        response = self.app.get(f"/api/requestQuestion/{session_id}")
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["content"], "Solve x+1=2")
        self.assertIn("questionId", data)
        
        # Verify pending question was inserted
        self.mock_pending.insert_one.assert_called_once()

    def test_submit_answer(self):
        question_id = "test_q_id"
        session_id = str(ObjectId())
        
        # Setup mock pending question
        self.mock_pending.find_one.return_value = {
            "questionId": question_id,
            "sessionID": session_id,
            "content": "Solve x+1=2",
            "aiAnswer": "x=1",
            "validation_prompt": "Validate",
            "metadata": {}
        }
        
        # Setup mock AI validation (Gemini)
        self.mock_ai.gemini.generate_json.return_value = {
            "ok": True,
            "feedback": "Good job"
        }
        
        response = self.app.post(f"/api/submitAnswer/{question_id}", 
                                 json={"answer": "x=1"})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["isCorrect"])
        self.assertEqual(data["correctAnswer"], "x=1")
        
        # Verify session was updated
        self.mock_sessions.update_one.assert_called_once()

    def test_request_hint(self):
        question_id = "test_q_id"
        
        # Setup mock pending question
        self.mock_pending.find_one.return_value = {
            "questionId": question_id,
            "content": "Solve x+1=2"
        }
        
        # Setup mock AI hint
        mock_hint = MagicMock()
        mock_hint.text = "Subtract 1"
        mock_hint.kind = "hint"
        self.mock_ai.generate_hint.return_value = mock_hint
        
        response = self.app.get(f"/api/requestHint/{question_id}")
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["hint"], "Subtract 1")

    def test_create_class(self):
        # Mock syllabus file
        from io import BytesIO
        syllabus_content = b"Syllabus content"
        data = {
            "syllabus": (BytesIO(syllabus_content), "syllabus.pdf"),
            "name": "Calculus 101",
            "professor": "Dr. Smith"
        }
        
        # Mock AI class file generation
        mock_class_file = MagicMock()
        mock_class_file.to_dict.return_value = {"syllabus": {}, "concepts": ["Limits"]}
        mock_class_file.concepts = ["Limits"]
        self.mock_ai.create_class_file_from_pdfs.return_value = mock_class_file
        
        # Mock Mongo insert
        self.mock_classes.insert_one.return_value.inserted_id = ObjectId()
        
        response = self.app.post("/api/createClass", data=data, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 200)
        self.mock_ai.create_class_file_from_pdfs.assert_called_once()
        self.mock_classes.insert_one.assert_called_once()
        
        # Verify inserted data has classFile and topics
        args, _ = self.mock_classes.insert_one.call_args
        inserted_doc = args[0]
        self.assertEqual(inserted_doc["topics"], ["Limits"])
        self.assertIsNotNone(inserted_doc["classFile"])

if __name__ == "__main__":
    unittest.main()
