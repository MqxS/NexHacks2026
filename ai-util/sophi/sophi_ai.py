from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import json
import os
import re
import time
import typing as t
import urllib.error
import urllib.parse
import urllib.request

from file_utils import FileUtils
from wolfram_checker import WolframAlphaChecker

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
        model: str = "gemini-flash-lite-latest",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_s: float = 60.0,
        tokenc_api_key: str | None = None,
        tokenc_aggressiveness: float = 0.3,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY).")
        self.model = os.environ.get("GEMINI_MODEL") or model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.tokenc_api_key = tokenc_api_key or os.environ.get("TOKENC_API_KEY")
        self.tokenc_enabled = str(os.environ.get("TOKENC_ENABLE") or "").strip().lower() in {"1", "true", "yes", "on"}
        self.tokenc_aggressiveness = float(tokenc_aggressiveness)
        self._tokenc_client: t.Any | None = None

    def _get_tokenc_client(self) -> t.Any | None:
        if not self.tokenc_api_key or not self.tokenc_enabled:
            return None
        if self._tokenc_client is not None:
            return self._tokenc_client
        try:
            from tokenc import TokenClient  # type: ignore
        except Exception:
            return None
        self._tokenc_client = TokenClient(api_key=self.tokenc_api_key)
        return self._tokenc_client

    def _compress_text(self, text: str) -> str:
        client = self._get_tokenc_client()
        if client is None:
            return text
        s = text.strip()
        if len(s) < 400:
            return text
        try:
            resp = client.compress_input(input=text, aggressiveness=self.tokenc_aggressiveness)
            
            # Log compression stats
            print(f"Compressed text: {getattr(resp, 'output', '')}")
            print(f"Original tokens: {getattr(resp, 'original_input_tokens', 0)}")
            print(f"Compressed tokens: {getattr(resp, 'output_tokens', 0)}")
            print(f"Tokens saved: {getattr(resp, 'tokens_saved', 0)}")
            print(f"Compression ratio: {getattr(resp, 'compression_ratio', 0.0):.2f}x")

            out = getattr(resp, "output", None)
            if isinstance(out, str) and out.strip():
                return out
        except Exception:
            return text
        return text

    def _compress_strings(self, obj: t.Any) -> t.Any:
        if isinstance(obj, str):
            return self._compress_text(obj)
        if isinstance(obj, list):
            return [self._compress_strings(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self._compress_strings(v) for k, v in obj.items()}
        return obj

    def _maybe_compress_prompt_text(self, text: str) -> str:
        client = self._get_tokenc_client()
        if client is None:
            return text
        s = text.lstrip()
        if s.startswith("{") or s.startswith("["):
            try:
                parsed = json.loads(text)
                compressed = self._compress_strings(parsed)
                return json.dumps(compressed, ensure_ascii=False)
            except Exception:
                return self._compress_text(text)
        return self._compress_text(text)

    def _strip_code_fences(self, text: str) -> str:
        s = text.strip()
        # Find the first opening fence
        start_fence = s.find("```")
        if start_fence != -1:
            # Check for language identifier (e.g., ```json)
            match = re.search(r"```[a-zA-Z0-9_-]*\s*", s[start_fence:])
            if match:
                content_start = start_fence + match.end()
                # Find the closing fence
                end_fence = s.find("```", content_start)
                if end_fence != -1:
                    return s[content_start:end_fence].strip()
                return s[content_start:].strip()
        return s

    def _extract_json_candidate(self, text: str) -> str:
        s = self._strip_code_fences(text)
        first_obj = s.find("{")
        first_arr = s.find("[")
        if first_obj == -1 and first_arr == -1:
            return s
        if first_obj == -1:
            start = first_arr
            end = s.rfind("]")
        elif first_arr == -1:
            start = first_obj
            end = s.rfind("}")
        else:
            start = min(first_obj, first_arr)
            end = s.rfind("}") if start == first_obj else s.rfind("]")
        if end == -1 or end <= start:
            return s[start:]
        return s[start : end + 1]

    def _escape_newlines_in_json_strings(self, text: str) -> str:
        out: list[str] = []
        in_str = False
        escape = False
        for ch in text:
            if in_str:
                if escape:
                    out.append(ch)
                    escape = False
                    continue
                if ch == "\\":
                    out.append(ch)
                    escape = True
                    continue
                if ch == '"':
                    out.append(ch)
                    in_str = False
                    continue
                if ch == "\n":
                    out.append("\\n")
                    continue
                if ch == "\r":
                    continue
                if ch == "\t":
                    out.append("\\t")
                    continue
                out.append(ch)
                continue
            if ch == '"':
                out.append(ch)
                in_str = True
                continue
            out.append(ch)
        return "".join(out)

    def _close_unbalanced_json(self, text: str) -> str:
        stack: list[str] = []
        in_str = False
        escape = False
        for ch in text:
            if in_str:
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_str = False
                continue

            if ch == '"':
                in_str = True
                continue
            if ch == "{":
                stack.append("}")
                continue
            if ch == "[":
                stack.append("]")
                continue
            if ch == "}" or ch == "]":
                if stack and stack[-1] == ch:
                    stack.pop()
                continue

        suffix = ""
        if in_str:
            suffix += '"'
        suffix += "".join(reversed(stack))
        return text + suffix

    def _repair_json_text(self, text: str) -> str:
        s = self._extract_json_candidate(text)
        s = self._escape_newlines_in_json_strings(s)
        s = self._close_unbalanced_json(s)
        s = re.sub(r",\s*([}\]])", r"\1", s)
        return s.strip()

    def _parse_model_json(self, text: str) -> JsonDict:
        # Always try to strip code fences first, as Gemini often wraps JSON in markdown
        cleaned = self._strip_code_fences(text)
        try:
            return t.cast(JsonDict, json.loads(cleaned))
        except json.JSONDecodeError:
            # Fallback to more aggressive repair
            repaired = self._repair_json_text(text)
            return t.cast(JsonDict, json.loads(repaired))

    def generate_json(
        self,
        *,
        system_instruction: str,
        user_prompt: str,
        few_shots: list[tuple[str, JsonDict]] | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 8192,
        image_bytes: bytes | None = None,
        image_mime_type: str = "image/png",
        allow_json_fix: bool = True,
    ) -> JsonDict:
        contents: list[JsonDict] = []

        if few_shots:
            for shot_user, shot_json in few_shots:
                contents.append({"role": "user", "parts": [{"text": self._maybe_compress_prompt_text(shot_user)}]})
                contents.append({"role": "model", "parts": [{"text": json.dumps(shot_json, ensure_ascii=False)}]})

        parts: list[JsonDict] = [{"text": self._maybe_compress_prompt_text(user_prompt)}]
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
            "systemInstruction": {"parts": [{"text": self._compress_text(system_instruction)}]},
            "contents": contents,
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
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
        def retry_delay_seconds(body_text: str | None) -> float | None:
            if not body_text:
                return None
            try:
                parsed = json.loads(body_text)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                err = parsed.get("error")
                if isinstance(err, dict):
                    details = err.get("details")
                    if isinstance(details, list):
                        for d in details:
                            if not isinstance(d, dict):
                                continue
                            if str(d.get("@type") or "").endswith("RetryInfo") and isinstance(d.get("retryDelay"), str):
                                m = re.search(r"(\d+)\s*s", d["retryDelay"])
                                if m:
                                    return float(m.group(1))
            m2 = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", body_text, flags=re.IGNORECASE)
            if m2:
                return float(m2.group(1))
            return None

        text = ""
        last_error: Exception | None = None
        
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    raw = resp.read().decode("utf-8")
                
                # Parse and validate immediately to trigger retry if empty
                try:
                    data = t.cast(JsonDict, json.loads(raw))
                except json.JSONDecodeError:
                    raise RuntimeError(f"Gemini returned invalid JSON: {raw[:1000]}")

                candidates = data.get("candidates") or []
                if not candidates:
                    raise RuntimeError("Gemini returned no candidates.")

                content = candidates[0].get("content") or {}
                parts = content.get("parts") or []
                text_parts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
                
                if not text_parts:
                    finish_reason = candidates[0].get("finishReason")
                    safety_ratings = candidates[0].get("safetyRatings")
                    raise RuntimeError(f"Gemini returned no text parts. Finish reason: {finish_reason}. Safety ratings: {safety_ratings}")
                
                text = "\n".join(t.cast(list[str], text_parts)).strip()
                break

            except urllib.error.HTTPError as e:
                body = None
                try:
                    body = e.read().decode("utf-8")
                except Exception:
                    body = None
                last_error = e
                if e.code == 429 and attempt < 2:
                    delay = retry_delay_seconds(body) or float(2 ** attempt) * 2.0
                    time.sleep(min(65.0, max(1.0, delay)))
                    continue
                raise RuntimeError(f"Gemini HTTPError {e.code}: {body}") from e
            
            except RuntimeError as e:
                last_error = e
                if attempt < 2:
                    # Retry on transient model errors (empty output, etc.)
                    time.sleep(float(2 ** attempt) * 1.0)
                    continue
                raise e

        if not text:
             # Should have raised in loop, but just in case
             raise RuntimeError("Gemini extraction failed.") from last_error
        try:
            return self._parse_model_json(text)
        except json.JSONDecodeError as e:
            if not allow_json_fix:
                raise RuntimeError(f"Gemini did not return valid JSON: {text[:4000]}") from e

            bad = text
            if len(bad) > 14000:
                bad = bad[:14000]
            fix_system = "You convert model output into valid JSON only."
            fix_prompt = json.dumps(
                {
                    "bad_text": bad,
                    "task": "Return valid JSON equivalent to bad_text. No markdown. No code fences.",
                },
                ensure_ascii=False,
            )
            return self.generate_json(
                system_instruction=fix_system,
                user_prompt=fix_prompt,
                few_shots=None,
                temperature=0.0,
                max_output_tokens=max_output_tokens,
                allow_json_fix=False,
            )


class SophiAIUtil:
    def __init__(
        self,
        *,
        gemini: GeminiClient | None = None,
        wolfram: WolframAlphaChecker | None = None,
        file_utils: FileUtils | None = None,
    ) -> None:
        self.gemini = gemini or GeminiClient()
        self.wolfram = wolfram
        if self.wolfram is None:
            try:
                self.wolfram = WolframAlphaChecker()
            except Exception:
                self.wolfram = None
        self.file_utils = file_utils or FileUtils()

    def _require_wolfram(self) -> WolframAlphaChecker:
        if self.wolfram is None:
            raise RuntimeError("Wolfram Alpha is disabled or WOLFRAM_APP_ID is missing.")
        return self.wolfram

    def _is_math_related(self, context_text: str) -> bool:
        """
        Determines if the subject context is suitable for Wolfram Alpha (Math, Physics, etc.).
        """
        if not context_text or not context_text.strip():
            return False

        system_instruction = (
            "Classify if the context is PURE MATH suitable for Wolfram Alpha symbolic solving. "
            "Strictly TRUE for: Calculus, Algebra, Geometry, Differential Equations, Physics calculations. "
            "Strictly FALSE for: Computer Science (CS1332, Data Structures, Algorithms), Coding, History, Literature, or general logic. "
            "Return JSON only: {\"is_math\": boolean}."
        )
        try:
            out = self.gemini.generate_json(
                system_instruction=system_instruction,
                user_prompt=json.dumps({"text": context_text}, ensure_ascii=False),
                temperature=0.0,
                max_output_tokens=128,
            )
            return bool(out.get("is_math"))
        except Exception as e:
            print(f"Error classifying subject: {e}")
            return False

    def evaluate_question_topics(
        self,
        *,
        question: str,
        class_topics: list[str],
    ) -> list[str]:
        if not class_topics:
            return []

        system_instruction = (
            "You are an expert curriculum evaluator. "
            "Given a question and a list of class topics, identify which of the class topics are present or tested in the question. "
            "Return JSON only: {\"topics\": [list of strings]}. "
            "The topics in the list must be exact matches from the provided class topics list."
        )

        user_prompt = json.dumps(
            {
                "question": question,
                "class_topics": class_topics,
            },
            ensure_ascii=False,
        )

        try:
            out = self.gemini.generate_json(
                system_instruction=system_instruction,
                user_prompt=user_prompt,
                temperature=0.0,
                max_output_tokens=512,
            )
            topics = out.get("topics")
            if isinstance(topics, list):
                # Filter to ensure they are actually in the class_topics list
                return [str(t) for t in topics if str(t) in class_topics]
            return []
        except Exception as e:
            print(f"Error evaluating topics: {e}")
            return []

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
        use_wolfram: bool = True,
    ) -> ValidationResult:
        if use_wolfram and not self._is_math_related(question):
            use_wolfram = False

        def coerce_dict(obj: t.Any) -> JsonDict | None:
            if isinstance(obj, dict):
                return t.cast(JsonDict, obj)
            if isinstance(obj, list):
                for it in obj:
                    if isinstance(it, dict):
                        return t.cast(JsonDict, it)
                return None
            return None

        if not use_wolfram:
            system_instruction = (
                "You determine if a question is well-posed and has a valid answer. "
                "If yes, provide a concise final answer. Return JSON only. "
                "Use LaTeX for math delimited by $$ ... $$. "
                "Do not include any preamble, markdown, or code fences."
            )
            few_shots = [
                (
                    json.dumps({"question": "Solve for x: 2x+3=11"}, ensure_ascii=False),
                    {"ok": True, "answer": "x=4", "explanation": "Linear equation with a unique solution."},
                ),
                (
                    json.dumps({"question": "What is the capital of France?"}, ensure_ascii=False),
                    {"ok": True, "answer": "Paris", "explanation": "Standard geography fact."},
                ),
                (
                    json.dumps({"question": "Solve for x: x=x+1"}, ensure_ascii=False),
                    {"ok": False, "answer": None, "explanation": "No solution exists."},
                ),
            ]
            out = self.gemini.generate_json(
                system_instruction=system_instruction,
                user_prompt=json.dumps(
                    {
                        "question": question,
                        "file_upload_text": file_upload_text,
                        "output_contract": {"ok": "boolean", "answer": "string | null", "explanation": "string"},
                    },
                    ensure_ascii=False,
                ),
                few_shots=few_shots,
                temperature=0.1,
                max_output_tokens=1024,
            )
            out_d = coerce_dict(out)
            if out_d is None:
                details = json.dumps(
                    {"answer": None, "explanation": str(out).strip()},
                    ensure_ascii=False,
                )
                return ValidationResult(ok=False, wolfram_query=None, wolfram_result=None, details=details)

            ok = bool(out_d.get("ok"))
            answer = out_d.get("answer")
            explanation = str(out_d.get("explanation") or "").strip()
            details = json.dumps(
                {"answer": None if answer is None else str(answer).strip(), "explanation": explanation},
                ensure_ascii=False,
            )
            return ValidationResult(ok=ok, wolfram_query=None, wolfram_result=None, details=details)

        system_instruction = (
            "You convert a math question into a single Wolfram Alpha query. "
            "Return JSON only. Do not include any preamble, markdown, or code fences."
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
        try:
            out = self.gemini.generate_json(
                system_instruction=system_instruction,
                user_prompt=user_prompt,
                few_shots=few_shots,
                temperature=0.1,
                max_output_tokens=512,
            )
        except Exception as e:
            return ValidationResult(ok=False, wolfram_query=None, wolfram_result=None, details=str(e))
        wolfram_query: str
        out_d = coerce_dict(out)
        if out_d is not None:
            wolfram_query = str(out_d.get("wolfram_query") or "").strip()
        elif isinstance(out, str):
            wolfram_query = out.strip()
        elif isinstance(out, list) and out and isinstance(out[0], str):
            wolfram_query = str(out[0]).strip()
        else:
            wolfram_query = ""
        if not wolfram_query:
            return ValidationResult(ok=False, wolfram_query=None, wolfram_result=None, details="missing_wolfram_query")
        ok, result = self._require_wolfram().best_effort_answer(wolfram_query)
        return ValidationResult(ok=ok, wolfram_query=wolfram_query or None, wolfram_result=result)

    def validate_hint_against_step(
        self,
        *,
        question: str,
        hint: str,
        current_step: str,
        hint_type: str | None = None,
        use_wolfram: bool = True,
    ) -> ValidationResult:
        if use_wolfram and not self._is_math_related(question):
            use_wolfram = False

        system_instruction = (
            "You verify whether a hint is consistent with a student's current step for a math problem. "
            "If possible, emit a Wolfram Alpha query that checks the key claim as a boolean or computation. "
            "Use LaTeX for math delimited by $$ ... $$. "
            "Return JSON only. Do not include any preamble, markdown, or code fences."
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
                        "question": "Who wrote 'The Great Gatsby'?",
                        "current_step": "I think it was Hemingway.",
                        "hint": "The author also wrote 'This Side of Paradise'.",
                        "hint_type": "Conceptual",
                    },
                    ensure_ascii=False,
                ),
                {
                    "is_consistent": True,
                    "wolfram_query": None,
                    "explanation": "F. Scott Fitzgerald wrote both; hint points away from Hemingway.",
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
            max_output_tokens=1024,
        )
        wolfram_query = out.get("wolfram_query")
        wolfram_query_s = str(wolfram_query).strip() if wolfram_query else ""
        wolfram_result = (
            self._require_wolfram().result_text(wolfram_query_s) if (use_wolfram and wolfram_query_s) else None
        )
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
        user_suggestions: str | None = None,
        max_attempts: int = 3,
        use_wolfram: bool = True,
    ) -> GeneratedQuestion:
        effective_session = dataclasses.replace(
            self.adjust_session_parameters(session, question_answer_history),
            unit_focus=unit_to_focus or session.unit_focus,
            focus_concepts=list(necessary_concepts or session.focus_concepts),
        ).normalized()

        if use_wolfram:
            parts = []
            if class_file and class_file.class_name:
                parts.append(f"Class: {class_file.class_name}")
            if effective_session.unit_focus:
                parts.append(f"Unit: {effective_session.unit_focus}")
            if effective_session.focus_concepts:
                parts.append(f"Concepts: {', '.join(effective_session.focus_concepts)}")
            
            context_str = " ".join(parts)
            if context_str and not self._is_math_related(context_str):
                use_wolfram = False

        system_instruction = (
            "You generate practice questions for a tutoring system. "
            "Return JSON only, with concise, student-friendly wording. "
            "Use LaTeX for math delimited by $$ ... $$. "
            "Do not include any preamble, markdown, or code fences. "
            "Always follow the provided output_contract. "
            "If must_be_solvable_in_wolfram_alpha=true, include a valid wolfram_query. "
            "If must_be_solvable_in_wolfram_alpha=false, include a correct final answer in the answer field. "
            "CRITICAL: If 'history' or 'class_file' is provided, you MUST analyze the style, tone, and complexity of the previous questions "
            "and generate the new question to MATCH that style exactly. Do not deviate from the established question format."
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
                    "answer": "x=7",
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
                    "answer": "5(4x-3)(2x^2-3x+1)^4",
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
                    "question": "Evaluate the definite integral $$\\int_{0}^{1} 2x\\,e^{x^2}\\,dx$$.",
                    "wolfram_query": "Integrate 2x*Exp[x^2] from 0 to 1",
                    "answer": "e-1",
                    "metadata": {"difficulty_level": 5, "concepts": ["definite integrals", "substitution"], "unit": "Calculus"},
                },
            ),
        ]

        history_tail = (question_answer_history or [])[-8:]
        class_file_payload = class_file.to_dict() if class_file else None

        # Determine adaptive behavior instruction
        adaptive_instruction = "None"
        if effective_session.adaptive and history_tail:
            last_q = history_tail[-1]
            was_correct = bool(last_q.get("correct"))
            if was_correct:
                adaptive_instruction = "The user answered the previous question CORRECTLY. Make this new question SLIGHTLY HARDER or more complex than the last one."
            else:
                adaptive_instruction = "The user answered the previous question INCORRECTLY. Make this new question SLIGHTLY EASIER or simpler than the last one."

        # Determine cumulative behavior instruction
        cumulative_instruction = "If cumulative=true, combine 2+ concepts; else isolate 1 concept."
        background_concepts: list[str] = []
        if effective_session.cumulative:
            if class_file:
                # Use concepts from class_file that are NOT in the current focus
                all_concepts = set(class_file.concepts)
                current_focus = set(effective_session.focus_concepts)
                background_concepts = list(all_concepts - current_focus)
                cumulative_instruction = (
                    "Cumulative is TRUE. You MUST combine the 'focus_concepts' with one or more 'background_concepts' "
                    "(older concepts provided in the payload). Do not rely ONLY on focus_concepts."
                )
            else:
                 cumulative_instruction = "Cumulative is TRUE. Integrate multiple concepts, including foundational ones implied by the difficulty level."

        def build_user_prompt(extra: JsonDict | None = None) -> str:
            payload: JsonDict = {
                "session": dataclasses.asdict(effective_session),
                "class_file": class_file_payload,
                "file_upload_text": file_upload_text,
                "user_suggestions": user_suggestions,
                "history": history_tail,
                "background_concepts": background_concepts,
                "requirements": {
                    "must_be_solvable_in_wolfram_alpha": bool(use_wolfram),
                    "if_not_using_wolfram_include_final_answer": True,
                    "question_should_not_repeat_recent": True,
                    "prefer_focus_concepts": effective_session.focus_concepts,
                    "cumulative_behavior": cumulative_instruction,
                    "adaptive_adjustment": adaptive_instruction,
                    "user_suggestions_instruction": "If 'user_suggestions' are provided, prioritize them highly in the question topic/style generation.",
                    "style_enforcement": "MIMIC the style of questions in 'history' and 'class_file.practice_problems' exactly.",
                },
                "output_contract": {
                    "question": "string",
                    "wolfram_query": "string",
                    "answer": "string",
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
                max_output_tokens=4096,
            )
            out_d: JsonDict | None
            if isinstance(out, dict):
                out_d = t.cast(JsonDict, out)
            elif isinstance(out, list):
                out_d = None
                for it in out:
                    if isinstance(it, dict):
                        out_d = t.cast(JsonDict, it)
                        break
            else:
                out_d = None

            if out_d is None:
                last_error = "invalid_output_shape"
                continue

            question = str(out_d.get("question") or "").strip()
            wolfram_query = str(out_d.get("wolfram_query") or "").strip()
            answer_llm = str(out_d.get("answer") or "").strip()
            if not question:
                last_error = "missing_question"
                continue
            if use_wolfram and not wolfram_query:
                last_error = "missing_wolfram_query"
                continue
            if not use_wolfram and not answer_llm:
                try:
                    v = self.validate_question_has_answer(
                        question=question,
                        file_upload_text=(file_upload_text[:2000] if file_upload_text else None),
                        use_wolfram=False,
                    )
                    if v.ok and v.details:
                        parsed = json.loads(v.details)
                        a0 = str(parsed.get("answer") or "").strip() if isinstance(parsed, dict) else ""
                        if a0:
                            answer_llm = a0
                except Exception:
                    pass
                if not answer_llm:
                    last_error = "missing_answer"
                    continue

            final_answer: str
            if use_wolfram:
                wa = self._require_wolfram().result_text(wolfram_query)
                if not wa or "Wolfram|Alpha did not understand" in wa:
                    last_error = f"wolfram_no_answer: {wa}"
                    continue
                final_answer = wa
            else:
                final_answer = answer_llm

            validation_prompt = self._build_validation_prompt(question=question)
            raw_metadata = out_d.get("metadata")
            metadata = t.cast(JsonDict, raw_metadata) if isinstance(raw_metadata, dict) else {}
            metadata.setdefault("difficulty_level", effective_session.difficulty_level)
            metadata.setdefault("concepts", effective_session.focus_concepts)
            metadata.setdefault("unit", effective_session.unit_focus)
            metadata.setdefault("cumulative", effective_session.cumulative)
            metadata.setdefault("adaptive", effective_session.adaptive)
            metadata.setdefault("verified_with_wolfram", bool(use_wolfram))
            if file_upload_text:
                metadata.setdefault("used_file_upload", True)
            if class_file:
                metadata.setdefault("used_class_file", True)

            return GeneratedQuestion(
                question=question,
                answer=final_answer,
                wolfram_query=wolfram_query if use_wolfram else "",
                validation_prompt=validation_prompt,
                metadata=metadata,
            )

        raise RuntimeError(f"Failed to generate verifiable question after {max_attempts} attempts: {last_error}")

    def _build_validation_prompt(self, *, question: str) -> str:
        system_instruction = (
            "You write a strict validation prompt for another AI model. "
            "It must evaluate a student's step-by-step work for a question. "
            "Return JSON only.\n"
            "IMPORTANT: The validation logic you describe MUST be robust to units. "
            "Instruct the verifier to accept answers where the numeric value is correct even if the unit is missing, "
            "abbreviated, or slightly different (e.g. '5 m/s', '5 meters per second', '5' are all acceptable if 5 is the correct number). "
            "If the unit is wrong (e.g. '5 kg' instead of '5 m'), mark it as incorrect."
        )
        few_shots = [
            (
                json.dumps({"question": "Solve for x: 2x+3=11"}, ensure_ascii=False),
                {
                    "validation_prompt": (
                        "You are a verifier. Given (1) the question and (2) a student's proposed next step, "
                        "decide if the step is logically valid. "
                        "Output JSON with keys: ok (boolean), error_type (string|null), feedback (string). "
                        "Be concise. Never reveal the final answer unless the student already did. "
                        "Ignore missing units if the number is correct."
                    )
                },
            )
        ]
        out = self.gemini.generate_json(
            system_instruction=system_instruction,
            user_prompt=json.dumps({"question": question, "output_contract": {"validation_prompt": "string"}}, ensure_ascii=False),
            few_shots=few_shots,
            temperature=0.1,
            max_output_tokens=2048,
        )
        return str(out.get("validation_prompt") or "").strip()

    def generate_hint(
        self,
        *,
        status_prompt: str,
        problem: str,
        hint_history: list[str] | None = None,
        hint_type: str | None = None,
        status_image_bytes: bytes | None = None,
        status_image_mime_type: str = "image/png",
        max_attempts: int = 2,
        use_wolfram: bool = True,
    ) -> HintResponse:
        if use_wolfram and not self._is_math_related(problem):
            use_wolfram = False

        system_instruction = (
            "You are a tutoring hint generator. "
            "You must either ask a single clarifying follow-up question, or provide a hint. "
            "If you provide a hint, keep it short and aligned with one of the hint types. "
            "Use LaTeX for math delimited by $$ ... $$. "
            "Whenever possible, supply a Wolfram Alpha query that can validate the key claim. "
            "If 'hint_history' is provided, do NOT repeat previous hints. Provide a progressively more helpful hint. "
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
                "hint_history": hint_history or [],
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
                max_output_tokens=2048,
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

            if not use_wolfram:
                return HintResponse(kind="hint", text=text, hint_type=ht, wolfram_query=None, wolfram_result=None)

            wolfram_result = self._require_wolfram().result_text(wq) if wq else None
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
            "Available request types: regenerate_question, save_metadata, adjust_session_parameter, create_class_file. "
            "Output contract: { \"request_type\": string, \"parameter_changes\": object, \"should_regenerate_question\": boolean, \"notes\": string } "
            "Return JSON only."
        )
        few_shots: list[tuple[str, JsonDict]] = [
            (
                json.dumps({"request_text": "Can you make the next question harder and focus on chain rule?"}, ensure_ascii=False),
                {
                    "request_type": "adjust_session_parameter",
                    "parameter_changes": {"difficulty_level_delta": 1, "focus_concepts_add": ["chain rule"]},
                    "should_regenerate_question": True,
                    "notes": "Increase difficulty slightly and focus on chain rule.",
                },
            ),
            (
                json.dumps({"request_text": "Regenerate this question; I already did something like it."}, ensure_ascii=False),
                {
                    "request_type": "regenerate_question",
                    "parameter_changes": {},
                    "should_regenerate_question": True,
                    "notes": "Avoid repeating the same structure.",
                },
            ),
            (
                json.dumps({"request_text": "Remember that I struggle with factoring; give me more of that later."}, ensure_ascii=False),
                {
                    "request_type": "save_metadata",
                    "parameter_changes": {"learner_profile_add": ["struggles_with_factoring"]},
                    "should_regenerate_question": False,
                    "notes": "Store as learner metadata for adaptiveness.",
                },
            ),
            (
                json.dumps({"request_text": "Create a class file for AP Calculus based on this syllabus and examples."}, ensure_ascii=False),
                {
                    "request_type": "create_class_file",
                    "parameter_changes": {},
                    "should_regenerate_question": False,
                    "notes": "Generate/refresh background class file.",
                },
            ),
        ]
        user_prompt = json.dumps({"request_text": request_text}, ensure_ascii=False)
        return self.gemini.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            few_shots=few_shots,
            temperature=0.1,
            max_output_tokens=1024,
        )
    
    def _generate_syllabus_section(self, syllabus_lines: list[str]) -> JsonDict:
        system_instruction = (
            "You convert a course syllabus text into a structured JSON outline. "
            "Return a JSON object with a single key 'syllabus' containing 'units'. "
            "Each unit has 'title' and 'topics'. "
            "STRICTLY process only the topic structure (units, modules, chapters, and their sub-topics). "
            "IGNORE all administrative details such as grading policies, attendance, office hours, exam dates, plagiarism policies, etc. "
            "Be comprehensive with the topics. Include all units found."
        )
        few_shots = [
            (
                json.dumps({"syllabus_raw": ["Unit 1: Limits", "- One-sided limits", "- Continuity"]}, ensure_ascii=False),
                {"syllabus": {"units": [{"title": "Limits", "topics": ["One-sided limits", "Continuity"]}]}},
            )
        ]
        user_prompt = json.dumps(
            {"syllabus_raw": syllabus_lines, "output_contract": {"syllabus": "object"}},
            ensure_ascii=False,
        )
        out = self.gemini.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            few_shots=few_shots,
            temperature=0.1,
            max_output_tokens=8192,
        )
        return t.cast(JsonDict, out.get("syllabus") or {})

    def _generate_concepts_section(self, syllabus_data: JsonDict) -> list[str]:
        system_instruction = (
            "You extract a list of core concepts from a syllabus structure. "
            "Return a JSON object with 'concepts', a list of strings. "
            "Focus ONLY on subject matter concepts (e.g., 'Integration', 'Photosynthesis'). "
            "Do NOT include administrative terms (e.g., 'Midterm', 'Grading'). "
            "Be comprehensive."
        )
        user_prompt = json.dumps(
            {"syllabus": syllabus_data, "output_contract": {"concepts": "string[]"}},
            ensure_ascii=False,
        )
        out = self.gemini.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            temperature=0.2,
            max_output_tokens=4096,
        )
        return list(out.get("concepts") or [])

    def _generate_practice_problems_section(self, problems_lines: list[str]) -> list[str]:
        if not problems_lines:
            return []
        system_instruction = (
            "You clean and select practice problems from a list of raw problems. "
            "Return a JSON object with 'practice_problems', a list of strings. "
            "Include up to 50 high-quality problems."
        )
        user_prompt = json.dumps(
            {"problems_raw": problems_lines, "output_contract": {"practice_problems": "string[]"}},
            ensure_ascii=False,
        )
        out = self.gemini.generate_json(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            temperature=0.1,
            max_output_tokens=8192,
        )
        return list(out.get("practice_problems") or [])

    def create_class_file(
        self,
        *,
        syllabus_text: str,
        practice_problems_text: str,
        class_name: str | None = None,
    ) -> ClassFile:
        scraped_syllabus = self.scrape_syllabus(syllabus_text)
        scraped_problems = self.scrape_practice_problems(practice_problems_text)

        syllabus_json = self._generate_syllabus_section(scraped_syllabus)
        concepts = self._generate_concepts_section(syllabus_json)
        practice_problems = self._generate_practice_problems_section(scraped_problems)

        return ClassFile(
            class_name=class_name,
            syllabus=syllabus_json,
            concepts=concepts,
            practice_problems=practice_problems,
            updated_at_iso=dt.datetime.now(dt.timezone.utc).isoformat(),
        )

    def parse_syllabus_pdf(
        self,
        *,
        syllabus_pdf_path: str,
        save_text_path: str | None = None,
        max_pages: int = 20,
    ) -> str:
        text = self.file_utils.extract_syllabus_outline(
            pdf_path=syllabus_pdf_path,
            gemini_client=self.gemini,
            max_pages=max_pages,
        )
        if save_text_path:
            self.file_utils.write_text(save_text_path, text)
        return text

    def parse_practice_problem_pdfs(
        self,
        *,
        problem_pdf_paths: list[str],
        save_text_path: str | None = None,
        max_pages_per_pdf: int = 20,
    ) -> list[str]:
        all_problems: list[str] = []
        for p in problem_pdf_paths:
            items = self.file_utils.extract_questions_answers_plaintext_latex(
                pdf_path=p,
                gemini_client=self.gemini,
                max_pages=max_pages_per_pdf,
            )
            for it in items:
                q = str(it.get("question") or "").strip()
                if not q:
                    continue
                a = it.get("answer")
                if isinstance(a, str) and a.strip():
                    all_problems.append(f"Question: {q}\nAnswer: {a.strip()}")
                else:
                    all_problems.append(q)
        if save_text_path:
            self.file_utils.write_text(save_text_path, "\n\n".join(all_problems))
        return all_problems

    def create_class_file_from_pdfs(
        self,
        *,
        syllabus_pdf_path: str,
        problem_pdf_paths: list[str],
        class_name: str | None = None,
        save_syllabus_text_path: str | None = None,
        save_problems_text_path: str | None = None,
        max_pages_per_pdf: int = 20,
    ) -> ClassFile:
        syllabus_text = self.parse_syllabus_pdf(
            syllabus_pdf_path=syllabus_pdf_path,
            save_text_path=save_syllabus_text_path,
            max_pages=max_pages_per_pdf,
        )
        problems = self.parse_practice_problem_pdfs(
            problem_pdf_paths=problem_pdf_paths,
            save_text_path=save_problems_text_path,
            max_pages_per_pdf=max_pages_per_pdf,
        )
        return self.create_class_file(
            syllabus_text=syllabus_text,
            practice_problems_text="\n".join(problems),
            class_name=class_name,
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
        return cleaned[:2000]

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
        return items[:1500]

    def _latex_to_plain_text(self, s: str) -> str:
        s = re.sub(r"\\\((.*?)\\\)", r"\1", s)
        s = re.sub(r"\\\[(.*?)\\\]", r"\1", s)
        s = re.sub(r"\$\$([^$]+)\$\$", r"\1", s)
        s = re.sub(r"\$([^$]+)\$", r"\1", s)
        s = s.replace("\\cdot", "*")
        s = s.replace("\\times", "*")
        s = s.replace("\\frac", "frac")
        s = re.sub(r"\\[a-zA-Z]+", "", s)
        s = s.replace("{", "").replace("}", "")
        s = re.sub(r"\s+", " ", s).strip()
        return s
