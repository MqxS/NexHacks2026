from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import json
import os
import re
import typing as t
import urllib.error
import urllib.parse
import urllib.request


JsonDict = dict[str, t.Any]


@dataclasses.dataclass(frozen=True)
class SessionParameters:
    difficulty_level: int
    cumulative: bool
    adaptive: bool
    focus_concepts: list[str]
    unit_focus: str | None = None

    def normalized(self) -> "SessionParameters":
        difficulty_level = int(self.difficulty_level)
        if difficulty_level < 1:
            difficulty_level = 1
        if difficulty_level > 5:
            difficulty_level = 5
        return dataclasses.replace(self, difficulty_level=difficulty_level)


@dataclasses.dataclass(frozen=True)
class QuestionRecord:
    question: str
    answer: str | None
    metadata: JsonDict
    wolfram_query: str | None
    validation_prompt: str | None
    created_at_iso: str


@dataclasses.dataclass(frozen=True)
class GeneratedQuestion:
    question: str
    answer: str
    wolfram_query: str
    validation_prompt: str
    metadata: JsonDict


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    ok: bool
    wolfram_query: str | None
    wolfram_result: str | None
    details: str | None = None


@dataclasses.dataclass(frozen=True)
class HintResponse:
    kind: t.Literal["followup", "hint"]
    text: str
    hint_type: str | None
    wolfram_query: str | None
    wolfram_result: str | None


@dataclasses.dataclass(frozen=True)
class ClassFile:
    class_name: str | None
    syllabus: JsonDict
    concepts: list[str]
    practice_problems: list[str]
    updated_at_iso: str

    def to_dict(self) -> JsonDict:
        return {
            "class_name": self.class_name,
            "syllabus": self.syllabus,
            "concepts": self.concepts,
            "practice_problems": self.practice_problems,
            "updated_at_iso": self.updated_at_iso,
        }

    @staticmethod
    def from_dict(data: JsonDict) -> "ClassFile":
        return ClassFile(
            class_name=data.get("class_name"),
            syllabus=t.cast(JsonDict, data.get("syllabus") or {}),
            concepts=list(data.get("concepts") or []),
            practice_problems=list(data.get("practice_problems") or []),
            updated_at_iso=str(data.get("updated_at_iso") or dt.datetime.now(dt.timezone.utc).isoformat()),
        )


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-1.5-pro-latest",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_s: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY).")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def generate_json(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        few_shots: list[tuple[str, JsonDict]] | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
        image_bytes: bytes | None = None,
        image_mime_type: str = "image/png",
    ) -> JsonDict:
        contents: list[JsonDict] = []

        if few_shots:
            for shot_user, shot_json in few_shots:
                contents.append({"role": "user", "parts": [{"text": shot_user}]})
                contents.append({"role": "model", "parts": [{"text": json.dumps(shot_json, ensure_ascii=False)}]})

        parts: list[JsonDict] = [{"text": user_prompt}]
        if image_bytes is not None:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": image_mime_type,
                        "data": base64.b64encode(image_bytes).decode("ascii"),
                    }
                }
            )
        contents.append({"role": "user", "parts": parts})

        payload: JsonDict = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
            },
        }

        url = f"{self.base_url}/models/{urllib.parse.quote(self.model)}:generateContent?key={urllib.parse.quote(self.api_key)}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = None
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass
            raise RuntimeError(f"Gemini HTTPError {e.code}: {body}") from e

        data = t.cast(JsonDict, json.loads(raw))
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")

        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        text_parts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
        if not text_parts:
            raise RuntimeError("Gemini returned no text parts.")

        text = "\n".join(t.cast(list[str], text_parts)).strip()
        try:
            return t.cast(JsonDict, json.loads(text))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Gemini did not return valid JSON: {text[:4000]}") from e


class WolframAlphaClient:
    def __init__(
        self,
        app_id: str | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.app_id = app_id or os.environ.get("WOLFRAM_APP_ID") or os.environ.get("WOLFRAM_APPID")
        if not self.app_id:
            raise RuntimeError("Missing WOLFRAM_APP_ID (or WOLFRAM_APPID).")
        self.timeout_s = timeout_s

    def result_text(self, query: str) -> str | None:
        q = query.strip()
        if not q:
            return None
        url = (
            "https://api.wolframalpha.com/v1/result?"
            + urllib.parse.urlencode({"i": q, "appid": self.app_id}, quote_via=urllib.parse.quote)
        )
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return resp.read().decode("utf-8").strip()
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8")
            except Exception:
                body = None
            if e.code in (400, 501):
                return None if not body else body.strip()
            raise


class SophiaAIUtil:
    def __init__(
        self,
        *,
        gemini: GeminiClient | None = None,
        wolfram: WolframAlphaClient | None = None,
    ) -> None:
        self.gemini = gemini or GeminiClient()
        self.wolfram = wolfram or WolframAlphaClient()

    def adjust_session_parameters(
        self,
        session: SessionParameters,
        question_answer_history: list[JsonDict] | None,
    ) -> SessionParameters:
        session = session.normalized()
        if not session.adaptive:
            return session

        history = question_answer_history or []
        recent = history[-6:]
        correctness = [bool(h.get("correct")) for h in recent if "correct" in h]
        if len(correctness) < 3:
            return session

        last3 = correctness[-3:]
        difficulty = session.difficulty_level
        if all(last3):
            difficulty += 1
        elif not any(last3):
            difficulty -= 1

        if difficulty < 1:
            difficulty = 1
        if difficulty > 5:
            difficulty = 5
        return dataclasses.replace(session, difficulty_level=difficulty)

    def validate_question_has_answer(
        self,
        *,
        question: str,
        file_upload_text: str | None = None,
    ) -> ValidationResult:
        system_instruction = (
            "You convert a math question into a single Wolfram Alpha query. "
            "Return JSON only."
        )
        few_shots = [
            (
                "Question: Solve for x: 2x+3=11",
                {"wolfram_query": "Solve 2x+3=11 for x"},
            ),
            (
                "Question: Evaluate the integral of x^2 from 0 to 3.",
                {"wolfram_query": "Integrate x^2 from 0 to 3"},
            ),
        ]
        user_prompt = json.dumps(
            {
                "question": question,
                "file_upload_text": file_upload_text,
                "output_contract": {"wolfram_query": "string"},
            },
            ensure_ascii=False,
        )
        out = self.gemini.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            few_shots=few_shots,
            temperature=0.1,
            max_output_tokens=256,
        )
        wolfram_query = str(out.get("wolfram_query") or "").strip()
        result = self.wolfram.result_text(wolfram_query)
        ok = bool(result) and ("Wolfram|Alpha did not understand" not in result)
        return ValidationResult(ok=ok, wolfram_query=wolfram_query or None, wolfram_result=result)

    def validate_hint_against_step(
        self,
        *,
        question: str,
        hint: str,
        current_step: str,
        hint_type: str | None = None,
    ) -> ValidationResult:
        system_instruction = (
            "You verify whether a hint is consistent with a student's current step for a math problem. "
            "If possible, emit a Wolfram Alpha query that checks the key claim as a boolean or computation. "
            "Return JSON only."
        )
        few_shots = [
            (
                json.dumps(
                    {
                        "question": "Solve 2x+3=11",
                        "current_step": "2x=8",
                        "hint": "Subtract 3 from both sides to isolate the 2x term.",
                        "hint_type": "Procedural / Subgoal",
                    },
                    ensure_ascii=False,
                ),
                {
                    "is_consistent": True,
                    "wolfram_query": "Simplify( (2x+3=11) && (2x=8) )",
                    "explanation": "Subtracting 3 from both sides is consistent with the step 2x=8.",
                },
            ),
            (
                json.dumps(
                    {
                        "question": "Compute derivative of x^2",
                        "current_step": "d/dx x^2 = 2x",
                        "hint": "The derivative is x.",
                        "hint_type": "Bottom-Out / Explicit",
                    },
                    ensure_ascii=False,
                ),
                {
                    "is_consistent": False,
                    "wolfram_query": "D[x^2,x]",
                    "explanation": "Derivative is 2x, not x.",
                },
            ),
        ]
        user_prompt = json.dumps(
            {
                "question": question,
                "current_step": current_step,
                "hint": hint,
                "hint_type": hint_type,
                "output_contract": {
                    "is_consistent": "boolean",
                    "wolfram_query": "string | null",
                    "explanation": "string",
                },
            },
            ensure_ascii=False,
        )
        out = self.gemini.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            few_shots=few_shots,
            temperature=0.1,
            max_output_tokens=512,
        )
        wolfram_query = out.get("wolfram_query")
        wolfram_query_s = str(wolfram_query).strip() if wolfram_query else ""
        wolfram_result = self.wolfram.result_text(wolfram_query_s) if wolfram_query_s else None
        is_consistent = bool(out.get("is_consistent"))
        return ValidationResult(
            ok=is_consistent,
            wolfram_query=wolfram_query_s or None,
            wolfram_result=wolfram_result,
            details=str(out.get("explanation") or "").strip() or None,
        )

    def generate_question(
        self,
        *,
        session: SessionParameters,
        question_answer_history: list[JsonDict] | None = None,
        necessary_concepts: list[str] | None = None,
        unit_to_focus: str | None = None,
        file_upload_text: str | None = None,
        class_file: ClassFile | None = None,
        max_attempts: int = 3,
    ) -> GeneratedQuestion:
        effective_session = dataclasses.replace(
            self.adjust_session_parameters(session, question_answer_history),
            unit_focus=unit_to_focus or session.unit_focus,
            focus_concepts=list(necessary_concepts or session.focus_concepts),
        ).normalized()

        system_instruction = (
            "You generate math practice questions for a tutoring system. "
            "You must produce a question that has a verifiable answer in Wolfram Alpha. "
            "Return JSON only, with concise, student-friendly wording."
        )
        few_shots: list[tuple[str, JsonDict]] = [
            (
                json.dumps(
                    {
                        "session": {
                            "difficulty_level": 1,
                            "cumulative": False,
                            "adaptive": False,
                            "focus_concepts": ["solving linear equations"],
                            "unit_focus": "Algebra I",
                        },
                        "history": [],
                    },
                    ensure_ascii=False,
                ),
                {
                    "question": "Solve for x: 3x - 5 = 16.",
                    "wolfram_query": "Solve 3x - 5 = 16 for x",
                    "metadata": {"difficulty_level": 1, "concepts": ["solving linear equations"], "unit": "Algebra I"},
                },
            ),
            (
                json.dumps(
                    {
                        "session": {
                            "difficulty_level": 3,
                            "cumulative": True,
                            "adaptive": False,
                            "focus_concepts": ["derivatives", "chain rule"],
                            "unit_focus": "Calculus",
                        },
                        "history": [{"question": "Differentiate x^3.", "correct": True}],
                    },
                    ensure_ascii=False,
                ),
                {
                    "question": "Differentiate f(x) = (2x^2 - 3x + 1)^5.",
                    "wolfram_query": "D[(2x^2 - 3x + 1)^5, x]",
                    "metadata": {"difficulty_level": 3, "concepts": ["derivatives", "chain rule"], "unit": "Calculus"},
                },
            ),
            (
                json.dumps(
                    {
                        "session": {
                            "difficulty_level": 5,
                            "cumulative": True,
                            "adaptive": True,
                            "focus_concepts": ["definite integrals", "substitution"],
                            "unit_focus": "Calculus",
                        },
                        "history": [{"question": "Integrate sin(x).", "correct": True}],
                    },
                    ensure_ascii=False,
                ),
                {
                    "question": "Evaluate the definite integral \\(\\int_{0}^{1} 2x\\,e^{x^2}\\,dx\\).",
                    "wolfram_query": "Integrate 2x*Exp[x^2] from 0 to 1",
                    "metadata": {"difficulty_level": 5, "concepts": ["definite integrals", "substitution"], "unit": "Calculus"},
                },
            ),
        ]

        history_tail = (question_answer_history or [])[-8:]
        class_file_payload = class_file.to_dict() if class_file else None

        def build_user_prompt(extra: JsonDict | None = None) -> str:
            payload: JsonDict = {
                "session": dataclasses.asdict(effective_session),
                "class_file": class_file_payload,
                "file_upload_text": file_upload_text,
                "history": history_tail,
                "requirements": {
                    "must_be_solvable_in_wolfram_alpha": True,
                    "question_should_not_repeat_recent": True,
                    "prefer_focus_concepts": effective_session.focus_concepts,
                    "cumulative_behavior": "If cumulative=true, combine 2+ concepts; else isolate 1 concept.",
                },
                "output_contract": {
                    "question": "string",
                    "wolfram_query": "string",
                    "metadata": "object",
                },
            }
            if extra:
                payload["extra"] = extra
            return json.dumps(payload, ensure_ascii=False)

        last_error: str | None = None
        for attempt in range(1, max_attempts + 1):
            out = self.gemini.generate_json(
                system_instruction=system_instruction,
                user_prompt=build_user_prompt({"attempt": attempt, "previous_issue": last_error}),
                few_shots=few_shots,
                temperature=0.2,
                max_output_tokens=900,
            )
            question = str(out.get("question") or "").strip()
            wolfram_query = str(out.get("wolfram_query") or "").strip()
            if not question or not wolfram_query:
                last_error = "missing_question_or_wolfram_query"
                continue

            wa = self.wolfram.result_text(wolfram_query)
            if not wa or "Wolfram|Alpha did not understand" in wa:
                last_error = f"wolfram_no_answer: {wa}"
                continue

            validation_prompt = self._build_validation_prompt(question=question)
            metadata = t.cast(JsonDict, out.get("metadata") or {})
            metadata.setdefault("difficulty_level", effective_session.difficulty_level)
            metadata.setdefault("concepts", effective_session.focus_concepts)
            metadata.setdefault("unit", effective_session.unit_focus)
            metadata.setdefault("cumulative", effective_session.cumulative)
            metadata.setdefault("adaptive", effective_session.adaptive)
            if file_upload_text:
                metadata.setdefault("used_file_upload", True)
            if class_file:
                metadata.setdefault("used_class_file", True)

            return GeneratedQuestion(
                question=question,
                answer=wa,
                wolfram_query=wolfram_query,
                validation_prompt=validation_prompt,
                metadata=metadata,
            )

        raise RuntimeError(f"Failed to generate verifiable question after {max_attempts} attempts: {last_error}")

    def _build_validation_prompt(self, *, question: str) -> str:
        system_instruction = (
            "You write a strict validation prompt for another AI model. "
            "It must evaluate a student's step-by-step work for a math question. "
            "Return JSON only."
        )
        few_shots = [
            (
                json.dumps({"question": "Solve for x: 2x+3=11"}, ensure_ascii=False),
                {
                    "validation_prompt": (
                        "You are a verifier. Given (1) the question and (2) a student's proposed next step, "
                        "decide if the step is logically valid. "
                        "Output JSON with keys: ok (boolean), error_type (string|null), feedback (string). "
                        "Be concise. Never reveal the final answer unless the student already did."
                    )
                },
            )
        ]
        out = self.gemini.generate_json(
            system_instruction=system_instruction,
            user_prompt=json.dumps({"question": question, "output_contract": {"validation_prompt": "string"}}, ensure_ascii=False),
            few_shots=few_shots,
            temperature=0.1,
            max_output_tokens=400,
        )
        return str(out.get("validation_prompt") or "").strip()

    def generate_hint(
        self,
        *,
        status_prompt: str,
        problem: str,
        hint_type: str | None = None,
        status_image_bytes: bytes | None = None,
        status_image_mime_type: str = "image/png",
        max_attempts: int = 2,
    ) -> HintResponse:
        system_instruction = (
            "You are a tutoring hint generator. "
            "You must either ask a single clarifying follow-up question, or provide a hint. "
            "If you provide a hint, keep it short and aligned with one of the hint types. "
            "Whenever possible, supply a Wolfram Alpha query that can validate the key claim. "
            "Return JSON only."
        )
        few_shots: list[tuple[str, JsonDict]] = [
            (
                json.dumps(
                    {
                        "problem": "Solve for x: 2x + 3 = 11",
                        "status_prompt": "I don't know what to do first.",
                        "hint_type": "Strategic",
                    },
                    ensure_ascii=False,
                ),
                {
                    "kind": "hint",
                    "hint_type": "Strategic",
                    "text": "Try isolating the x-term first by undoing the +3, then undo the multiplication by 2.",
                    "wolfram_query": "Solve 2x+3=11 for x",
                },
            ),
            (
                json.dumps(
                    {
                        "problem": "Evaluate the limit: lim_{x->0} (sin x)/x",
                        "status_prompt": "I wrote sin(0)/0 and got 0/0. Is that bad?",
                        "hint_type": None,
                    },
                    ensure_ascii=False,
                ),
                {
                    "kind": "hint",
                    "hint_type": "Conceptual",
                    "text": "Getting 0/0 means you need a limit technique (like a known special limit or series), not direct substitution.",
                    "wolfram_query": "Limit[Sin[x]/x, x->0]",
                },
            ),
            (
                json.dumps(
                    {
                        "problem": "Find the derivative of f(x)=x^2",
                        "status_prompt": "My work is: derivative is 2x. Still not sure why.",
                        "hint_type": None,
                    },
                    ensure_ascii=False,
                ),
                {
                    "kind": "followup",
                    "hint_type": None,
                    "text": "Which rule did you use (power rule, definition of derivative, or something else)?",
                    "wolfram_query": None,
                },
            ),
        ]

        def build_user_prompt(extra: JsonDict | None = None) -> str:
            payload: JsonDict = {
                "problem": problem,
                "status_prompt": status_prompt,
                "hint_type": hint_type,
                "hint_types": [
                    "Metacognitive / Reflection",
                    "Conceptual",
                    "Strategic",
                    "Procedural / Subgoal",
                    "Bottom-Out / Explicit",
                ],
                "output_contract": {
                    "kind": '"followup" | "hint"',
                    "hint_type": "string | null",
                    "text": "string",
                    "wolfram_query": "string | null",
                },
            }
            if extra:
                payload["extra"] = extra
            return json.dumps(payload, ensure_ascii=False)

        last_issue: str | None = None
        last_out: JsonDict | None = None
        for attempt in range(1, max_attempts + 1):
            out = self.gemini.generate_json(
                system_instruction=system_instruction,
                user_prompt=build_user_prompt({"attempt": attempt, "previous_issue": last_issue}),
                few_shots=few_shots,
                temperature=0.2,
                max_output_tokens=700,
                image_bytes=status_image_bytes,
                image_mime_type=status_image_mime_type,
            )
            last_out = out

            kind = str(out.get("kind") or "").strip()
            text = str(out.get("text") or "").strip()
            inferred_hint_type = out.get("hint_type")
            ht = str(inferred_hint_type).strip() if inferred_hint_type else None
            wolfram_query = out.get("wolfram_query")
            wq = str(wolfram_query).strip() if wolfram_query else None

            if kind not in ("followup", "hint") or not text:
                last_issue = "invalid_kind_or_missing_text"
                continue

            if kind == "followup":
                return HintResponse(kind="followup", text=text, hint_type=None, wolfram_query=None, wolfram_result=None)

            wolfram_result = self.wolfram.result_text(wq) if wq else None
            if wq and wolfram_result and "Wolfram|Alpha did not understand" not in wolfram_result:
                return HintResponse(kind="hint", text=text, hint_type=ht, wolfram_query=wq, wolfram_result=wolfram_result)

            last_issue = "wolfram_unverifiable_hint"

        fallback_text = str((last_out or {}).get("text") or "").strip()
        return HintResponse(
            kind="hint",
            text=fallback_text,
            hint_type=hint_type,
            wolfram_query=None,
            wolfram_result=None,
        )

    def analyze_settings_request(self, *, request_text: str) -> JsonDict:
        system_instruction = (
            "You classify a user's request about a practice session into an action. "
            "Return JSON only."
        )
        few_shots: list[tuple[str, JsonDict]] = [
            (
                "Request: Can you make the next question harder and focus on chain rule?",
                {
                    "request_type": "adjust_session_parameter",
                    "parameter_changes": {"difficulty_level_delta": 1, "focus_concepts_add": ["chain rule"]},
                    "should_regenerate_question": True,
                    "notes": "Increase difficulty slightly and focus on chain rule.",
                },
            ),
            (
                "Request: Regenerate this question; I already did something like it.",
                {
                    "request_type": "regenerate_question",
                    "parameter_changes": {},
                    "should_regenerate_question": True,
                    "notes": "Avoid repeating the same structure.",
                },
            ),
            (
                "Request: Remember that I struggle with factoring; give me more of that later.",
                {
                    "request_type": "save_metadata",
                    "parameter_changes": {"learner_profile_add": ["struggles_with_factoring"]},
                    "should_regenerate_question": False,
                    "notes": "Store as learner metadata for adaptiveness.",
                },
            ),
            (
                "Request: Create a class file for AP Calculus based on this syllabus and examples.",
                {
                    "request_type": "create_class_file",
                    "parameter_changes": {},
                    "should_regenerate_question": False,
                    "notes": "Generate/refresh background class file.",
                },
            ),
        ]
        user_prompt = json.dumps(
            {
                "request_text": request_text,
                "request_types": [
                    "regenerate_question",
                    "save_metadata",
                    "adjust_session_parameter",
                    "create_class_file",
                ],
                "output_contract": {
                    "request_type": "string",
                    "parameter_changes": "object",
                    "should_regenerate_question": "boolean",
                    "notes": "string",
                },
            },
            ensure_ascii=False,
        )
        return self.gemini.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            few_shots=few_shots,
            temperature=0.1,
            max_output_tokens=450,
        )

    def create_class_file(
        self,
        *,
        syllabus_text: str,
        practice_problems_text: str,
        class_name: str | None = None,
    ) -> ClassFile:
        scraped_syllabus = self.scrape_syllabus(syllabus_text)
        scraped_problems = self.scrape_practice_problems(practice_problems_text)

        system_instruction = (
            "You create a compact 'class file' JSON used to generate practice problems. "
            "Syllabus is hierarchical. Produce a list of core concepts and a cleaned practice problem bank. "
            "Return JSON only."
        )
        few_shots: list[tuple[str, JsonDict]] = [
            (
                json.dumps(
                    {
                        "class_name": "Algebra I",
                        "syllabus_raw": ["Unit 1: Linear Equations", "  - One-step equations", "  - Two-step equations"],
                        "problems_raw": ["Solve 2x+3=11", "Graph y=2x-5"],
                    },
                    ensure_ascii=False,
                ),
                {
                    "syllabus": {"units": [{"title": "Linear Equations", "topics": ["One-step equations", "Two-step equations"]}]},
                    "concepts": ["solving linear equations", "graphing lines"],
                    "practice_problems": ["Solve for x: 2x + 3 = 11.", "Graph the line y = 2x - 5."],
                },
            )
        ]
        user_prompt = json.dumps(
            {
                "class_name": class_name,
                "syllabus_raw": scraped_syllabus,
                "problems_raw": scraped_problems,
                "output_contract": {
                    "syllabus": "object",
                    "concepts": "string[]",
                    "practice_problems": "string[]",
                },
            },
            ensure_ascii=False,
        )
        out = self.gemini.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            few_shots=few_shots,
            temperature=0.2,
            max_output_tokens=1200,
        )
        return ClassFile(
            class_name=class_name,
            syllabus=t.cast(JsonDict, out.get("syllabus") or {}),
            concepts=list(out.get("concepts") or []),
            practice_problems=list(out.get("practice_problems") or []),
            updated_at_iso=dt.datetime.now(dt.timezone.utc).isoformat(),
        )

    def save_class_file(self, *, path: str, class_file: ClassFile) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(class_file.to_dict(), f, ensure_ascii=False, indent=2)

    def load_class_file(self, *, path: str) -> ClassFile:
        with open(path, "r", encoding="utf-8") as f:
            data = t.cast(JsonDict, json.load(f))
        return ClassFile.from_dict(data)

    def save_question_record_jsonl(self, *, path: str, record: QuestionRecord) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(dataclasses.asdict(record), ensure_ascii=False) + "\n")

    def record_from_generated(self, *, generated: GeneratedQuestion) -> QuestionRecord:
        return QuestionRecord(
            question=generated.question,
            answer=generated.answer,
            metadata=generated.metadata,
            wolfram_query=generated.wolfram_query,
            validation_prompt=generated.validation_prompt,
            created_at_iso=dt.datetime.now(dt.timezone.utc).isoformat(),
        )

    def scrape_syllabus(self, text: str) -> list[str]:
        lines = [ln.strip() for ln in (text or "").splitlines()]
        lines = [ln for ln in lines if ln and not re.fullmatch(r"[-–—]{3,}", ln)]
        cleaned: list[str] = []
        for ln in lines:
            ln = re.sub(r"\s+", " ", ln).strip()
            if not ln:
                continue
            cleaned.append(ln)
        return cleaned[:800]

    def scrape_practice_problems(self, text: str) -> list[str]:
        raw_lines = [ln.strip() for ln in (text or "").splitlines()]
        raw_lines = [ln for ln in raw_lines if ln]
        joined = "\n".join(raw_lines)
        blocks = re.split(r"\n\s*\n+", joined)
        items: list[str] = []
        for blk in blocks:
            b = blk.strip()
            if not b:
                continue
            b = re.sub(r"\s+", " ", b)
            b = self._latex_to_plain_text(b)
            items.append(b.strip())
        return items[:500]

    def _latex_to_plain_text(self, s: str) -> str:
        s = re.sub(r"\\\((.*?)\\\)", r"\1", s)
        s = re.sub(r"\\\[(.*?)\\\]", r"\1", s)
        s = re.sub(r"\$([^$]+)\$", r"\1", s)
        s = s.replace("\\cdot", "*")
        s = s.replace("\\times", "*")
        s = s.replace("\\frac", "frac")
        s = re.sub(r"\\[a-zA-Z]+", "", s)
        s = s.replace("{", "").replace("}", "")
        s = re.sub(r"\s+", " ", s).strip()
        return s
