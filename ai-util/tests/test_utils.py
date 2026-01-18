from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import logging
import pathlib
import sys
import traceback
import typing as t

JsonDict = dict[str, t.Any]


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def _ai_util_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


def _sample_classes_root() -> pathlib.Path:
    return _ai_util_root() / "sample_classes"


def _logs_root() -> pathlib.Path:
    return _ai_util_root() / "tests" / "logs"


def _configure_logging(*, class_dir_name: str) -> tuple[logging.Logger, pathlib.Path]:
    _logs_root().mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = _logs_root() / f"{class_dir_name}__{ts}.log"

    logger = logging.getLogger("sophia_test_utils")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)

    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger, log_path


def _safe_json(obj: t.Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def _list_pdfs(class_dir: pathlib.Path) -> tuple[pathlib.Path, list[pathlib.Path]]:
    syllabus = class_dir / "syllabus.pdf"
    if not syllabus.exists():
        raise FileNotFoundError(f"Missing syllabus.pdf in {class_dir}")
    others = sorted([p for p in class_dir.glob("*.pdf") if p.name != "syllabus.pdf"])
    return syllabus, others


def _load_env(logger: logging.Logger) -> None:
    ai_util_root = _ai_util_root()
    if str(ai_util_root) not in sys.path:
        sys.path.insert(0, str(ai_util_root))

    try:
        import set_env_vars
    except Exception:
        logger.info("Could not import set_env_vars.py; skipping env initialization.")
        return

    try:
        status = set_env_vars.initialize_env_vars()
    except Exception:
        logger.info("set_env_vars.initialize_env_vars failed; continuing.")
        return

    logger.info("Environment status: %s", _safe_json(status))


def _import_sophia(logger: logging.Logger) -> tuple[t.Any, t.Any, t.Any]:
    sophia_dir = _ai_util_root() / "sophia"
    if str(sophia_dir) not in sys.path:
        sys.path.insert(0, str(sophia_dir))
    try:
        import sophia_ai as sophia_ai_mod
        import wolfram_checker as wolfram_checker_mod
    except Exception as e:
        logger.info("Import failed: %s", str(e))
        raise
    return sophia_ai_mod, wolfram_checker_mod, sophia_dir


def _run_for_class_dir(
    *,
    class_dir: pathlib.Path,
    max_pages: int,
    logger: logging.Logger,
) -> JsonDict:
    class_name = class_dir.name
    is_math = class_name.startswith("math-")
    use_wolfram = bool(is_math)

    sophia_ai_mod, wolfram_checker_mod, sophia_dir = _import_sophia(logger)

    WolframAlphaChecker = wolfram_checker_mod.WolframAlphaChecker
    SophiaAIUtil = sophia_ai_mod.SophiaAIUtil
    SessionParameters = sophia_ai_mod.SessionParameters

    logger.info("Repo root: %s", str(_repo_root()))
    logger.info("ai-util root: %s", str(_ai_util_root()))
    logger.info("Sophia module dir: %s", str(sophia_dir))
    logger.info("Selected class dir: %s", str(class_dir))
    logger.info("Class type: %s", "math (wolfram enabled)" if use_wolfram else "non-math (wolfram disabled)")

    syllabus_pdf, practice_pdfs = _list_pdfs(class_dir)
    logger.info("syllabus.pdf: %s", str(syllabus_pdf))
    logger.info("practice PDFs: %d", len(practice_pdfs))
    for p in practice_pdfs:
        logger.info(" - %s", p.name)

    practice_pdfs = practice_pdfs[:2]

    wolfram = None
    if use_wolfram:
        try:
            wolfram = WolframAlphaChecker()
        except Exception as e:
            logger.info("Wolfram init failed; continuing with wolfram disabled: %s", str(e))
            wolfram = None
            use_wolfram = False

    ai = SophiaAIUtil(wolfram=wolfram)

    artifacts_dir = _logs_root() / f"{class_dir.name}__artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    syllabus_text_path = artifacts_dir / "syllabus_extracted.txt"
    problems_text_path = artifacts_dir / "practice_items_extracted.txt"
    class_file_path = artifacts_dir / "class_file.json"
    history_path = artifacts_dir / "question_history.jsonl"

    logger.info("Artifacts dir: %s", str(artifacts_dir))

    def is_quota_error(exc: BaseException) -> bool:
        msg = str(exc)
        if "HTTPError 429" in msg:
            return True
        if "RESOURCE_EXHAUSTED" in msg:
            return True
        low = msg.lower()
        if "quota" in low and "exceed" in low:
            return True
        return False

    def run_step(*, name: str, fn: t.Callable[[], t.Any]) -> tuple[t.Any, JsonDict]:
        logger.info("%s...", name)
        try:
            val = fn()
            return val, {"name": name, "ok": True, "skipped": False, "error": None}
        except Exception as e:
            skipped = is_quota_error(e)
            logger.info("%s %s: %s", name, "SKIPPED" if skipped else "FAILED", str(e))
            logger.info("Traceback:\n%s", traceback.format_exc())
            return None, {"name": name, "ok": False, "skipped": skipped, "error": str(e)}

    syllabus_text, step_syllabus = run_step(
        name="Parsing syllabus PDF",
        fn=lambda: ai.parse_syllabus_pdf(
            syllabus_pdf_path=str(syllabus_pdf),
            save_text_path=str(syllabus_text_path),
            max_pages=max_pages,
        ),
    )
    syllabus_text = t.cast(str | None, syllabus_text)
    logger.info("Syllabus extracted chars: %d", len(syllabus_text or ""))

    practice_items, step_practice = run_step(
        name="Parsing practice PDFs",
        fn=lambda: ai.parse_practice_problem_pdfs(
            problem_pdf_paths=[str(p) for p in practice_pdfs],
            save_text_path=str(problems_text_path),
            max_pages_per_pdf=max_pages,
        ),
    )
    practice_items = t.cast(list[str] | None, practice_items)
    logger.info("Practice items extracted: %d", len(practice_items or []))
    sample_items = (practice_items or [])[:3]
    if sample_items:
        logger.info("Sample practice items:\n%s", "\n\n".join(sample_items))

    loaded_class_file = None
    step_class_file = {"name": "Creating class file from PDFs", "ok": False, "skipped": True, "error": "Skipped due to earlier failures"}
    if step_syllabus["ok"] or step_practice["ok"]:
        class_file, step_class_file = run_step(
            name="Creating class file from PDFs",
            fn=lambda: ai.create_class_file_from_pdfs(
                syllabus_pdf_path=str(syllabus_pdf),
                problem_pdf_paths=[str(p) for p in practice_pdfs],
                class_name=class_dir.name,
                save_syllabus_text_path=str(syllabus_text_path),
                save_problems_text_path=str(problems_text_path),
                max_pages_per_pdf=max_pages,
            ),
        )
        if class_file is not None:
            ai.save_class_file(path=str(class_file_path), class_file=class_file)
            loaded_class_file = ai.load_class_file(path=str(class_file_path))
            logger.info("Class file saved: %s", str(class_file_path))
            logger.info("Class file concepts: %d", len(loaded_class_file.concepts))

    session = SessionParameters(
        difficulty_level=3,
        cumulative=True,
        adaptive=True,
        focus_concepts=loaded_class_file.concepts[:5] if (loaded_class_file and loaded_class_file.concepts) else ["practice"],
        unit_focus=class_dir.name,
    )

    history: list[JsonDict] = [
        {"question": "Warmup question", "correct": True},
        {"question": "Another question", "correct": True},
        {"question": "Harder question", "correct": False},
    ]
    adjusted = ai.adjust_session_parameters(session, history)
    logger.info("Adjusted session: %s", _safe_json(adjusted.__dict__))

    generated = None
    step_generate = {"name": "Generating question", "ok": False, "skipped": True, "error": "Skipped due to earlier failures"}
    if loaded_class_file is not None and not step_class_file.get("skipped"):
        generated, step_generate = run_step(
            name="Generating question",
            fn=lambda: ai.generate_question(
                session=adjusted,
                question_answer_history=history,
                file_upload_text=(syllabus_text or "")[:2500] if syllabus_text else None,
                class_file=loaded_class_file,
                use_wolfram=use_wolfram,
            ),
        )

    if generated is not None:
        logger.info("Generated question:\n%s", generated.question)
        logger.info("Generated answer:\n%s", generated.answer)
        logger.info("Verified with wolfram: %s", str(bool(generated.metadata.get("verified_with_wolfram"))))
        logger.info("Validation prompt length: %d", len(generated.validation_prompt))

        record = ai.record_from_generated(generated=generated)
        ai.save_question_record_jsonl(path=str(history_path), record=record)
        logger.info("Saved question record: %s", str(history_path))

    generated_with_suggestion = None
    step_generate_suggestion = {"name": "Generating question with suggestions", "ok": False, "skipped": True, "error": "Skipped due to earlier failures"}
    if loaded_class_file is not None and not step_class_file.get("skipped"):
        generated_with_suggestion, step_generate_suggestion = run_step(
            name="Generating question with suggestions",
            fn=lambda: ai.generate_question(
                session=adjusted,
                question_answer_history=history,
                file_upload_text=None,
                class_file=loaded_class_file,
                user_suggestions="Make the question involve space travel or dinosaurs.",
                use_wolfram=use_wolfram,
            ),
        )

    if generated_with_suggestion is not None:
        logger.info("Generated question (with suggestions):\n%s", generated_with_suggestion.question)
        logger.info("Generated answer (with suggestions):\n%s", generated_with_suggestion.answer)

    v_ok = None
    step_v_ok = {"name": "Validating question (expected valid)", "ok": False, "skipped": True, "error": "Skipped"}
    if generated is not None:
        v_ok, step_v_ok = run_step(
            name="Validating question (expected valid)",
            fn=lambda: ai.validate_question_has_answer(
                question=generated.question,
                file_upload_text=(syllabus_text or "")[:2000] if syllabus_text else None,
                use_wolfram=use_wolfram,
            ),
        )
        if v_ok is not None:
            logger.info("Validation ok=%s wolfram_query=%s", str(v_ok.ok), str(v_ok.wolfram_query))

    bad_question = "Solve for x: x = x +"
    v_bad, step_v_bad = run_step(
        name="Validating question (expected invalid)",
        fn=lambda: ai.validate_question_has_answer(
            question=bad_question,
            file_upload_text=None,
            use_wolfram=use_wolfram,
        ),
    )
    if v_bad is not None:
        logger.info(
            "Bad validation ok=%s wolfram_query=%s wolfram_result=%s",
            str(v_bad.ok),
            str(v_bad.wolfram_query),
            str(v_bad.wolfram_result),
        )

    hint_types = [
        "Metacognitive / Reflection",
        "Conceptual",
        "Strategic",
        "Procedural / Subgoal",
        "Bottom-Out / Explicit",
    ]
    hint_results = {}
    hint_steps = {}

    if generated is not None:
        for ht in hint_types:
            h_res, h_step = run_step(
                name=f"Generating hint ({ht})",
                fn=lambda ht=ht: ai.generate_hint(
                    status_prompt="I am stuck and unsure what to do next.",
                    problem=generated.question,
                    hint_type=ht,
                    use_wolfram=use_wolfram,
                ),
            )
            hint_steps[ht] = h_step
            if h_res is not None:
                hint_results[ht] = h_res
                logger.info("Hint (%s) kind=%s type=%s\n%s", ht, h_res.kind, str(h_res.hint_type), h_res.text)

    v_hint, step_v_hint = run_step(
        name="Validating hint against a step",
        fn=lambda: ai.validate_hint_against_step(
            question="Solve for x: 2x + 3 = 11",
            hint="The derivative is x.",
            current_step="2x=8",
            hint_type="Bottom-Out / Explicit",
            use_wolfram=use_wolfram,
        ),
    )
    if v_hint is not None:
        logger.info("Hint validation ok=%s wolfram_query=%s", str(v_hint.ok), str(v_hint.wolfram_query))

    settings_requests = [
        ("adjust_session_parameter", "Can you make the next question harder and focus on chain rule?"),
        ("regenerate_question", "Regenerate this question; I already did something like it."),
        ("save_metadata", "Remember that I struggle with factoring; give me more of that later."),
        ("create_class_file", "Create a class file for AP Calculus based on this syllabus and examples."),
    ]

    settings_results = []
    settings_steps = {}

    for req_type, req_text in settings_requests:
        s_res, s_step = run_step(
            name=f"Analyzing settings request ({req_type})",
            fn=lambda rt=req_text: ai.analyze_settings_request(request_text=rt),
        )
        settings_steps[req_type] = s_step
        if s_res is not None:
            logger.info("Settings analysis (%s): %s", req_type, _safe_json(s_res))
        settings_results.append(s_res)

    return {
        "class_dir": str(class_dir),
        "is_math": is_math,
        "use_wolfram": use_wolfram,
        "syllabus_chars": len(syllabus_text or ""),
        "practice_items_count": len(practice_items or []),
        "steps": {
            "parse_syllabus": step_syllabus,
            "parse_practice": step_practice,
            "create_class_file": step_class_file,
            "generate_question": step_generate,
            "generate_question_with_suggestion": step_generate_suggestion,
            "validate_ok": step_v_ok,
            "validate_bad": step_v_bad,
            "validate_hint": step_v_hint,
            **hint_steps,
            **settings_steps,
        },
        "generated": dataclasses_asdict_safe(generated) if generated is not None else None,
        "generated_with_suggestion": dataclasses_asdict_safe(generated_with_suggestion) if generated_with_suggestion is not None else None,
        "validation_ok": dataclasses_asdict_safe(v_ok) if v_ok is not None else None,
        "validation_bad": dataclasses_asdict_safe(v_bad) if v_bad is not None else None,
        "hints": {k: dataclasses_asdict_safe(v) for k, v in hint_results.items()},
        "hint_validation": dataclasses_asdict_safe(v_hint) if v_hint is not None else None,
        "settings_analyses": [s for s in settings_results if s is not None],
        "artifacts_dir": str(artifacts_dir),
    }


def dataclasses_asdict_safe(obj: t.Any) -> JsonDict:
    if dataclasses.is_dataclass(obj):
        return t.cast(JsonDict, dataclasses.asdict(obj))
    if hasattr(obj, "__dict__"):
        return t.cast(JsonDict, obj.__dict__)
    return {"value": str(obj)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "class_dir",
        help="Folder name under ai-util/sample_classes (e.g. math-calculus-bc or cs1332)",
    )
    parser.add_argument("--max-pages", type=int, default=8)
    args = parser.parse_args(argv)

    logger, log_path = _configure_logging(class_dir_name=args.class_dir)
    logger.info("Log file: %s", str(log_path))

    _load_env(logger)
    class_dir = _sample_classes_root() / args.class_dir
    if not class_dir.exists() or not class_dir.is_dir():
        logger.info("Class directory not found: %s", str(class_dir))
        return 1

    results = _run_for_class_dir(class_dir=class_dir, max_pages=args.max_pages, logger=logger)
    results_path = log_path.with_suffix(".json")
    pathlib.Path(results_path).write_text(_safe_json(results), encoding="utf-8")
    logger.info("Saved results JSON: %s", str(results_path))
    logger.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
