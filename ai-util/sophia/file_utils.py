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
        max_pages: int = 12,
    ) -> list[str]:
        extracted = self.extract_text_from_pdf(pdf_path)
        if self._looks_like_useful_text(extracted):
            return self._format_problems_with_gemini(extracted, gemini_client=gemini_client)

        page_images = self._pdf_to_png_pages(pdf_path, max_pages=max_pages)
        if not page_images:
            return []

        all_problems: list[str] = []
        for img in page_images:
            all_problems.extend(self._extract_problems_from_image(img, gemini_client=gemini_client))

        deduped: list[str] = []
        seen: set[str] = set()
        for p in all_problems:
            k = re.sub(r"\s+", " ", p).strip().lower()
            if not k or k in seen:
                continue
            seen.add(k)
            deduped.append(p.strip())
        return deduped

    def extract_syllabus_text(
        self,
        *,
        pdf_path: str,
        gemini_client: t.Any,
        max_pages: int = 12,
    ) -> str:
        extracted = self.extract_text_from_pdf(pdf_path)
        if self._looks_like_useful_text(extracted):
            return extracted

        page_images = self._pdf_to_png_pages(pdf_path, max_pages=max_pages)
        if not page_images:
            return ""

        chunks: list[str] = []
        for img in page_images:
            chunks.append(self._extract_syllabus_from_image(img, gemini_client=gemini_client))
        return self._normalize_extracted_text("\n\n".join([c for c in chunks if c.strip()]))

    def _extract_text_with_pypdf(self, pdf_path: str) -> str | None:
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception:
            try:
                from PyPDF2 import PdfReader  # type: ignore
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
                cmd = ["pdftoppm", "-png", "-r", "200", "-f", "1", "-l", str(max_pages), pdf_path, prefix]
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
            "Preserve mathematical expressions using LaTeX delimited by \\( ... \\) or \\[ ... \\]. "
            "Return JSON only."
        )
        few_shots = [
            (
                "Input text:\n1) Solve 2x+3=11\n2) Integral_0^1 2x e^{x^2} dx",
                {
                    "problems": [
                        "Solve for x: \\(2x + 3 = 11\\).",
                        "Evaluate \\(\\int_{0}^{1} 2x e^{x^2} \\, dx\\).",
                    ]
                },
            )
        ]
        out = gemini_client.generate_json(
            system_instruction=system_instruction,
            user_prompt=t.cast(str, self._json_dump({"text": extracted_text, "output_contract": {"problems": "string[]"}})),
            few_shots=few_shots,
            temperature=0.2,
            max_output_tokens=1200,
        )
        problems = out.get("problems") or []
        if not isinstance(problems, list):
            return []
        cleaned = [str(p).strip() for p in problems if str(p).strip()]
        return cleaned

    def _extract_problems_from_image(self, image_bytes: bytes, *, gemini_client: t.Any) -> list[str]:
        system_instruction = (
            "You read an image of a worksheet or textbook page and extract the practice problems. "
            "Write them as plain text with LaTeX for math, using \\( ... \\) or \\[ ... \\]. "
            "Return JSON only."
        )
        few_shots = [
            (
                "Extract problems from the page image. Return JSON.",
                {"problems": ["Solve for x: \\(3x-5=16\\).", "Differentiate \\(f(x)=(x^2+1)^3\\)."]},
            )
        ]
        out = gemini_client.generate_json(
            system_instruction=system_instruction,
            user_prompt=t.cast(str, self._json_dump({"output_contract": {"problems": "string[]"}})),
            few_shots=few_shots,
            temperature=0.1,
            max_output_tokens=1200,
            image_bytes=image_bytes,
            image_mime_type="image/png",
        )
        problems = out.get("problems") or []
        if not isinstance(problems, list):
            return []
        return [str(p).strip() for p in problems if str(p).strip()]

    def _extract_syllabus_from_image(self, image_bytes: bytes, *, gemini_client: t.Any) -> str:
        system_instruction = (
            "You read an image of a course syllabus page and extract the unit/topic outline. "
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
            max_output_tokens=900,
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

    def _normalize_extracted_text(self, text: str) -> str:
        s = text.replace("\r\n", "\n").replace("\r", "\n")
        s = re.sub(r"[ \t]+\n", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        s = re.sub(r"[ \t]{2,}", " ", s)
        return s.strip()

    def _json_dump(self, obj: dict[str, t.Any]) -> str:
        import json

        return json.dumps(obj, ensure_ascii=False)

