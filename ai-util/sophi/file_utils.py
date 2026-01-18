from __future__ import annotations

import os
import re
import subprocess
import tempfile
import typing as t


class FileUtils:
    def read_bytes(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def write_text(self, path: str, text: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        text = self._extract_text_with_pypdf(pdf_path)
        if text and text.strip():
            return self._normalize_extracted_text(text)

        text = self._extract_text_with_pdftotext(pdf_path)
        if text and text.strip():
            return self._normalize_extracted_text(text)

        return ""

    def extract_text_from_pdfs(self, pdf_paths: list[str]) -> str:
        parts: list[str] = []
        for p in pdf_paths:
            parts.append(self.extract_text_from_pdf(p))
        return "\n\n".join([p for p in parts if p.strip()])

    def extract_problems_plaintext_latex(
        self,
        *,
        pdf_path: str,
        gemini_client: t.Any,
        max_pages: int = 20,
    ) -> list[str]:
        items = self.extract_questions_answers_plaintext_latex(
            pdf_path=pdf_path,
            gemini_client=gemini_client,
            max_pages=max_pages,
        )
        return [it["question"] for it in items if it.get("question")]

    def extract_questions_answers_plaintext_latex(
        self,
        *,
        pdf_path: str,
        gemini_client: t.Any,
        max_pages: int = 20,
    ) -> list[dict[str, str | None]]:
        extracted = self.extract_text_from_pdf(pdf_path)
        if self._looks_like_useful_text(extracted):
            items = self._format_qa_with_gemini(extracted, gemini_client=gemini_client)
            return self._dedupe_qa(items)

        page_images = self._pdf_to_png_pages(pdf_path, max_pages=max_pages)
        if not page_images:
            pdf_bytes = self.read_bytes(pdf_path)
            return self._dedupe_qa(self._extract_qa_from_pdf_bytes(pdf_bytes, gemini_client=gemini_client, max_pages=max_pages))

        all_items: list[dict[str, str | None]] = []
        for img in page_images:
            all_items.extend(self._extract_qa_from_image(img, gemini_client=gemini_client))
        return self._dedupe_qa(all_items)

    def extract_syllabus_text(
        self,
        *,
        pdf_path: str,
        gemini_client: t.Any,
        max_pages: int = 20,
    ) -> str:
        return self.extract_syllabus_outline(pdf_path=pdf_path, gemini_client=gemini_client, max_pages=max_pages)

    def extract_syllabus_outline(
        self,
        *,
        pdf_path: str,
        gemini_client: t.Any,
        max_pages: int = 20,
    ) -> str:
        extracted = self.extract_text_from_pdf(pdf_path)
        if self._looks_like_useful_text(extracted):
            return self._format_syllabus_with_gemini(extracted, gemini_client=gemini_client)

        page_images = self._pdf_to_png_pages(pdf_path, max_pages=max_pages)
        if not page_images:
            pdf_bytes = self.read_bytes(pdf_path)
            return self._extract_syllabus_from_pdf_bytes(pdf_bytes, gemini_client=gemini_client, max_pages=max_pages)

        chunks: list[str] = []
        for img in page_images:
            chunks.append(self._extract_syllabus_from_image(img, gemini_client=gemini_client))
        merged = self._normalize_extracted_text("\n\n".join([c for c in chunks if c.strip()]))
        if not merged:
            return ""
        return self._format_syllabus_with_gemini(merged, gemini_client=gemini_client)

    def _extract_text_with_pypdf(self, pdf_path: str) -> str | None:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except Exception:
            try:
                from pypdf import PdfReader  # type: ignore
            except Exception:
                return None

        try:
            reader = PdfReader(pdf_path)
            texts: list[str] = []
            for page in reader.pages:
                t0 = page.extract_text() or ""
                if t0.strip():
                    texts.append(t0)
            return "\n\n".join(texts)
        except Exception:
            return None

    def _split_pdf_bytes(self, pdf_bytes: bytes, max_pages: int = 10) -> list[bytes]:
        import io

        try:
            from PyPDF2 import PdfReader, PdfWriter  # type: ignore
        except Exception:
            try:
                from pypdf import PdfReader, PdfWriter  # type: ignore
            except Exception:
                return [pdf_bytes]

        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            total_pages = len(reader.pages)
            if total_pages <= max_pages:
                return [pdf_bytes]

            chunks: list[bytes] = []
            for i in range(0, total_pages, max_pages):
                writer = PdfWriter()
                # Create a new writer for each chunk to avoid accumulation issues
                for page in reader.pages[i : i + max_pages]:
                    writer.add_page(page)

                with io.BytesIO() as out:
                    writer.write(out)
                    chunks.append(out.getvalue())
            return chunks
        except Exception:
            return [pdf_bytes]

    def _extract_text_with_pdftotext(self, pdf_path: str) -> str | None:
        candidates: list[list[str]] = [
            ["pdftotext", "-layout", pdf_path, "-"],
            ["pdftotext", pdf_path, "-"],
        ]
        for cmd in candidates:
            try:
                p = subprocess.run(cmd, check=False, capture_output=True, text=True)
            except FileNotFoundError:
                return None
            if p.returncode == 0 and p.stdout and p.stdout.strip():
                return p.stdout

        try:
            with tempfile.TemporaryDirectory() as td:
                out_path = os.path.join(td, "out.txt")
                p = subprocess.run(["pdftotext", "-layout", pdf_path, out_path], check=False, capture_output=True, text=True)
                if p.returncode != 0:
                    return None
                with open(out_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
        except FileNotFoundError:
            return None

    def _pdf_to_png_pages(self, pdf_path: str, *, max_pages: int) -> list[bytes]:
        try:
            with tempfile.TemporaryDirectory() as td:
                prefix = os.path.join(td, "page")
                cmd = ["pdftoppm", "-png", "-r", "200", "-f", "1", pdf_path, prefix]
                p = subprocess.run(cmd, check=False, capture_output=True)
                if p.returncode != 0:
                    return []
                files = sorted([os.path.join(td, f) for f in os.listdir(td) if f.endswith(".png")])
                out: list[bytes] = []
                for fp in files:
                    with open(fp, "rb") as f:
                        out.append(f.read())
                return out
        except FileNotFoundError:
            return []

    def _format_problems_with_gemini(self, extracted_text: str, *, gemini_client: t.Any) -> list[str]:
        system_instruction = (
            "You clean up extracted PDF text into a list of distinct practice problems. "
            "Preserve mathematical expressions using LaTeX delimited by $$ ... $$. "
            "Return at most 60 problems. "
            "Return JSON only."
        )
        few_shots = [
            (
                "Input text:\n1) Solve 2x+3=11\n2) Integral_0^1 2x e^{x^2} dx",
                {
                    "problems": [
                        "Solve for x: $$2x + 3 = 11$$.",
                        "Evaluate $$\\int_{0}^{1} 2x e^{x^2} \\, dx$$.",
                    ]
                },
            )
        ]
        out = gemini_client.generate_json(
            system_instruction=system_instruction,
            user_prompt=t.cast(
                str,
                self._json_dump({"text": extracted_text, "max_items": 60, "output_contract": {"problems": "string[]"}}),
            ),
            few_shots=few_shots,
            temperature=0.2,
            max_output_tokens=8192,
        )
        problems: t.Any
        if isinstance(out, list):
            problems = out
        else:
            problems = out.get("problems") if isinstance(out, dict) else []
        if not isinstance(problems, list):
            return []
        cleaned = [str(p).strip() for p in problems if str(p).strip()]
        return cleaned

    def _format_qa_with_gemini(self, extracted_text: str, *, gemini_client: t.Any) -> list[dict[str, str | None]]:
        # Split text into chunks to ensure coverage and avoid output limits
        chunk_size = 40000
        chunks = [extracted_text[i : i + chunk_size] for i in range(0, len(extracted_text), chunk_size)]
        all_items: list[dict[str, str | None]] = []

        system_instruction = (
            "You convert extracted PDF text into a list of practice items. Each item should have a question and, "
            "if an answer key is present, an answer. Preserve math as LaTeX using $$ ... $$. "
            "Return at most 60 items. "
            "Return JSON only."
        )
        few_shots = [
            (
                "Input text:\n1) Solve 2x+3=11\nAnswer: x=4\n\n2) Find d/dx x^2\nAnswer: 2x",
                {
                    "items": [
                        {"question": "Solve for x: $$2x + 3 = 11$$.", "answer": "$$x=4$$"},
                        {"question": "Differentiate $$x^2$$.", "answer": "$$2x$$"},
                    ]
                },
            ),
            (
                "Input text:\n(1) Evaluate integral from 0 to 1 of 2x e^{x^2} dx\n(no answers provided)",
                {
                    "items": [
                        {
                            "question": "Evaluate $$\\int_{0}^{1} 2x e^{x^2} \\, dx$$.",
                            "answer": None,
                        }
                    ]
                },
            ),
        ]

        for chunk in chunks:
            out = gemini_client.generate_json(
                system_instruction=system_instruction,
                user_prompt=t.cast(
                    str,
                    self._json_dump(
                        {
                            "text": chunk,
                            "max_items": 60,
                            "output_contract": {"items": [{"question": "string", "answer": "string | null"}]},
                        }
                    ),
                ),
                few_shots=few_shots,
                temperature=0.2,
                max_output_tokens=8192,
            )
            items: t.Any
            if isinstance(out, list):
                items = out
            else:
                items = out.get("items") if isinstance(out, dict) else []
            if isinstance(items, list):
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    q = str(it.get("question") or "").strip()
                    if not q:
                        continue
                    a_raw = it.get("answer")
                    a = None if a_raw is None else str(a_raw).strip()
                    all_items.append({"question": q, "answer": a if a else None})

        return self._dedupe_qa(all_items)

    def _extract_problems_from_image(self, image_bytes: bytes, *, gemini_client: t.Any) -> list[str]:
        system_instruction = (
            "You read an image of a worksheet or textbook page and extract the practice problems. "
            "Write them as plain text with LaTeX for math, using $$ ... $$. "
            "Return at most 60 problems. "
            "Return JSON only."
        )
        few_shots = [
            (
                "Extract problems from the page image. Return JSON.",
                {"problems": ["Solve for x: $$3x-5=16$$.", "Differentiate $$f(x)=(x^2+1)^3$$."]},
            )
        ]
        out = gemini_client.generate_json(
            system_instruction=system_instruction,
            user_prompt=t.cast(str, self._json_dump({"max_items": 60, "output_contract": {"problems": "string[]"}})),
            few_shots=few_shots,
            temperature=0.1,
            max_output_tokens=4096,
            image_bytes=image_bytes,
            image_mime_type="image/png",
        )
        problems = out.get("problems") or []
        if not isinstance(problems, list):
            return []
        return [str(p).strip() for p in problems if str(p).strip()]

    def _extract_qa_from_image(self, image_bytes: bytes, *, gemini_client: t.Any) -> list[dict[str, str | None]]:
        system_instruction = (
            "You read an image of a worksheet, practice exam, or textbook page and extract practice items. "
            "Each item should have a question and, if the answer is visible on the page, an answer. "
            "Preserve math as LaTeX using $$ ... $$. "
            "Return at most 60 items. "
            "Return JSON only."
        )
        few_shots = [
            (
                "Extract practice items from the page image. Return JSON.",
                {
                    "items": [
                        {"question": "Solve for x: $$3x-5=16$$.", "answer": None},
                        {"question": "Differentiate $$f(x)=(x^2+1)^3$$.", "answer": None},
                    ]
                },
            )
        ]
        out = gemini_client.generate_json(
            system_instruction=system_instruction,
            user_prompt=t.cast(
                str,
                self._json_dump({"max_items": 60, "output_contract": {"items": [{"question": "string", "answer": "string | null"}]}}),
            ),
            few_shots=few_shots,
            temperature=0.1,
            max_output_tokens=8192,
            image_bytes=image_bytes,
            image_mime_type="image/png",
        )
        items = out.get("items") or []
        if not isinstance(items, list):
            return []
        cleaned: list[dict[str, str | None]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            q = str(it.get("question") or "").strip()
            if not q:
                continue
            a_raw = it.get("answer")
            a = None if a_raw is None else str(a_raw).strip()
            cleaned.append({"question": q, "answer": a if a else None})
        return cleaned

    def _extract_qa_from_pdf_bytes(
        self,
        pdf_bytes: bytes,
        *,
        gemini_client: t.Any,
        max_pages: int,
    ) -> list[dict[str, str | None]]:
        # Split PDF into manageable chunks to avoid token limits and improve extraction yield
        chunks = self._split_pdf_bytes(pdf_bytes, max_pages=10)
        all_items: list[dict[str, str | None]] = []

        system_instruction = (
            "You read a PDF of a worksheet, practice exam, or textbook pages and extract practice items. "
            "Each item should have a question and, if an answer key is present, an answer. "
            "Preserve math as LaTeX using $$ ... $$. "
            "Return JSON only."
        )
        few_shots = [
            (
                "Extract practice items from the PDF. Return JSON.",
                {
                    "items": [
                        {"question": "Solve for x: $$3x-5=16$$.", "answer": None},
                        {"question": "Differentiate $$x^2$$.", "answer": "$$2x$$"},
                    ]
                },
            )
        ]

        for chunk in chunks:
            out = gemini_client.generate_json(
                system_instruction=system_instruction,
                user_prompt=t.cast(
                    str,
                    self._json_dump(
                        {
                            "max_items": 100,
                            "output_contract": {"items": [{"question": "string", "answer": "string | null"}]},
                        }
                    ),
                ),
                few_shots=few_shots,
                temperature=0.1,
                max_output_tokens=8192,
                image_bytes=chunk,
                image_mime_type="application/pdf",
            )
            items: t.Any
            if isinstance(out, list):
                items = out
            else:
                items = out.get("items") if isinstance(out, dict) else None
                if items is None and isinstance(out, dict):
                    items = out.get("output") or out.get("data")
                items = items or []
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict):
                        q = str(it.get("question") or "").strip()
                        if q:
                            a_raw = it.get("answer")
                            a = None if a_raw is None else str(a_raw).strip()
                            all_items.append({"question": q, "answer": a if a else None})

        return self._dedupe_qa(all_items)

    def _format_syllabus_with_gemini(self, extracted_text: str, *, gemini_client: t.Any) -> str:
        system_instruction = (
            "You convert messy syllabus text into a clean unit/topic outline. "
            "Be comprehensive and include all units and topics found. Preserve course-specific names. "
            "STRICTLY exclude administrative info (grading, policies, instructors, office hours). "
            "Return JSON only."
        )
        few_shots = [
            (
                "Input text:\nUNIT 1 LIMITS (weeks 1-2) one sided limits continuity\nUNIT 2 DERIVATIVES power rule chain rule",
                {"syllabus_text": "Unit 1: Limits\n- One-sided limits\n- Continuity\n\nUnit 2: Derivatives\n- Power rule\n- Chain rule"},
            )
        ]
        out = gemini_client.generate_json(
            system_instruction=system_instruction,
            user_prompt=t.cast(str, self._json_dump({"text": extracted_text, "output_contract": {"syllabus_text": "string"}})),
            few_shots=few_shots,
            temperature=0.2,
            max_output_tokens=8192,
        )
        if isinstance(out, dict):
            return str(out.get("syllabus_text") or "").strip()
        if isinstance(out, str):
            return out.strip()
        if isinstance(out, list):
            parts = [str(x).strip() for x in out if str(x).strip()]
            return "\n".join(parts).strip()
        return ""

    def _extract_syllabus_from_pdf_bytes(
        self,
        pdf_bytes: bytes,
        *,
        gemini_client: t.Any,
        max_pages: int,
    ) -> str:
        chunks = self._split_pdf_bytes(pdf_bytes, max_pages=10)
        extracted_parts: list[str] = []

        system_instruction = (
            "You read a PDF course syllabus and extract the unit/topic outline. "
            "Be comprehensive with topics. "
            "STRICTLY exclude administrative info (grading, policies, instructors, office hours). "
            "Return JSON only."
        )
        few_shots = [
            (
                "Extract the syllabus outline from the PDF. Return JSON.",
                {"syllabus_text": "Unit 1: Limits\n- One-sided limits\n- Continuity\n\nUnit 2: Derivatives\n- Power rule\n- Chain rule"},
            )
        ]

        for chunk in chunks:
            out = gemini_client.generate_json(
                system_instruction=system_instruction,
                user_prompt=t.cast(
                    str,
                    self._json_dump({"output_contract": {"syllabus_text": "string"}}),
                ),
                few_shots=few_shots,
                temperature=0.1,
                max_output_tokens=8192,
                image_bytes=chunk,
                image_mime_type="application/pdf",
            )
            text = ""
            if isinstance(out, dict):
                text = str(out.get("syllabus_text") or "").strip()
            elif isinstance(out, str):
                text = out.strip()
            if text:
                extracted_parts.append(text)

        return "\n\n".join(extracted_parts).strip()

    def _extract_syllabus_from_image(self, image_bytes: bytes, *, gemini_client: t.Any) -> str:
        system_instruction = (
            "You read an image of a course syllabus page and extract the unit/topic outline. "
            "Be comprehensive with topics. "
            "STRICTLY exclude administrative info (grading, policies, instructors, office hours). "
            "Return JSON only."
        )
        few_shots = [
            (
                "Extract the syllabus outline from the image. Return JSON.",
                {"syllabus_text": "Unit 1: Limits\n- One-sided limits\n- Continuity\n\nUnit 2: Derivatives\n- Power rule\n- Chain rule"},
            )
        ]
        out = gemini_client.generate_json(
            system_instruction=system_instruction,
            user_prompt=t.cast(str, self._json_dump({"output_contract": {"syllabus_text": "string"}})),
            few_shots=few_shots,
            temperature=0.1,
            max_output_tokens=8192,
            image_bytes=image_bytes,
            image_mime_type="image/png",
        )
        return str(out.get("syllabus_text") or "").strip()

    def _looks_like_useful_text(self, text: str) -> bool:
        t0 = (text or "").strip()
        if len(t0) < 200:
            return False
        if len(re.findall(r"[A-Za-z]", t0)) < 80:
            return False
        return True

    def _dedupe_qa(self, items: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
        out: list[dict[str, str | None]] = []
        seen: set[str] = set()
        for it in items:
            q = str(it.get("question") or "").strip()
            if not q:
                continue
            key = re.sub(r"\s+", " ", q).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            a = it.get("answer")
            out.append({"question": q, "answer": a.strip() if isinstance(a, str) and a.strip() else None})
        return out

    def _normalize_extracted_text(self, text: str) -> str:
        s = text.replace("\r\n", "\n").replace("\r", "\n")
        s = re.sub(r"[ \t]+\n", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        s = re.sub(r"[ \t]{2,}", " ", s)
        return s.strip()

    def _json_dump(self, obj: dict[str, t.Any]) -> str:
        import json

        return json.dumps(obj, ensure_ascii=False)
