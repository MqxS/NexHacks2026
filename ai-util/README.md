# $so\varphi$: The golden ratio for practice

$so\varphi$ (pronounced *Sophie*) is the golden ratio for practice, providing excellent hints and generating questions in the style of your own professor - so you never have to redo old practice tests.

Need to set the following environment variables:
*   `TOKENC_API_KEY` - The API key for the TokenC API.
*   `GEMINI_API_KEY` - The API key for the Gemini API.
*   `WOLFRAM_APP_ID` - The API key for the Wolfram API.

Test $so\varphi$ with the following commands (command-line unit tests):

```
python ai-util/tests/test_utils.py math-calculus-bc
python ai-util/tests/test_utils.py cs1332
```

## Inspiration
Studying is often inefficient not because students lack effort, but because practice materials rarely adapt to *how* a specific class is taught or *where* a student is struggling. Problem sets are static, difficulty is poorly calibrated, and feedback loops are slow. We wanted to build something that feels like a personalized practice environment—one that understands your syllabus, your professor’s style, and your current level of understanding, then evolves with you as you practice. **Sophi** was inspired by the idea that practice should feel closer to a one-on-one tutor than a generic worksheet.

---

## What it does
Sophi is an adaptive practice platform that generates personalized free-response questions tailored to a specific class. Users organize their coursework into **Classes**, each containing multiple **Sessions**—individual practice environments with configurable parameters like difficulty, topic focus, and adaptivity.

Each session dynamically generates questions, validates answers, provides targeted hints, explains mistakes, and adjusts future questions based on user performance. Over time, Sophi builds a deep understanding of the class structure, content, and teaching style to deliver increasingly precise and effective practice.

---

## How we built it
Sophi is structured around a few core abstractions:

- **Class**: A collection of practice sets for a given course.
- **Session**: A single practice environment with configurable parameters.
- **Class File (JSON)**: Auto-generated metadata containing:
  - Topic breakdown (indented syllabus-style hierarchy)
  - Textbook citation (if applicable)
  - Style-notes derived from assignments (professor vocabulary, problem structure, common phrasing)

Early design decisions included:
- Starting with **free-response questions only** to encourage deeper reasoning.
- Restricting answers to **numerical responses** where appropriate for reliable validation.
- Building adaptive behavior at the session level rather than globally.

The backend maintains session context across interactions, ensuring hints, feedback, and follow-ups are part of a continuous conversation rather than isolated prompts.

---

## Challenges we ran into
- **Modeling “difficulty”** as a continuous value from 0 to 1 while keeping it intuitive for users.
- Translating unstructured documents (syllabi, homework PDFs) into a clean, hierarchical topic map.
- Maintaining long-running conversational context across hints without degrading relevance.
- Balancing adaptivity with user control—knowing when to challenge versus reinforce.
- Designing UI flows that expose powerful configuration without overwhelming users.

---

## Accomplishments that we're proud of
- A clean abstraction between **Classes**, **Sessions**, and adaptive logic.
- Automatic regeneration of the class-file when core documents change.
- Fine-grained control over practice parameters while keeping sensible defaults.
- Context-aware hinting that adapts based on where the user is stuck.
- A scalable foundation for cumulative learning across sessions.

---

## What we learned
- Students value *control* as much as adaptivity—toggles and transparency matter.
- Professor style has a huge impact on how questions should be framed.
- Difficulty is not just about harder math; it’s about abstraction, wording, and conceptual load.
- Practice feels more effective when the system acknowledges past mistakes explicitly.
- Small UX touches (like searchable topic dropdowns) dramatically improve usability.

---

## What's next for Sophi
