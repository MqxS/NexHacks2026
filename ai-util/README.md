# $so\varphi$: The golden ratio for practice

$so\varphi$ (pronounced *Sophie*), named after *wisdom* in Greek, aims to bridge the gap between traditional practice tests and personalized, adaptive learning. By leveraging instructor-offered practice problems, $so\varphi$ not only adapts the difficulty and content to match the student's current level, but also ensures that the questions are aligned with the professor's teaching style.

## Admin Stuff

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
**Sophi** was inspired by the idea that practice should feel closer to a one-on-one tutor than a generic worksheet, with the goal to solve the following problems:
*   Notoriously, most professors offer only two to three practice sets for each exam, leaving most students with no choice but to redo the homework and practice exams, or consult "non-canon" resources
*   As a student, we have little other choice than to view the practice solutions - there are currently no autonomous ways to 
*   Bullet about creating an adaptive workflow to maximize the ROI of studying



Each of us faced this same problem in our first semester as freshmen, with professors not being able to and our goal is to 

We know this market is saturated, but pride ourselves on the ability to leverage LLM customization to mimic instructor-style problem generation.

## What it does
Sophi is an adaptive practice platform that generates personalized free-response questions tailored to a specific class. Users organize their coursework into **Classes**, each containing multiple **Sessions**—individual practice environments with configurable parameters like difficulty, topic focus, and adaptivity.

Each session dynamically generates questions, validates answers, provides targeted hints, explains mistakes, and adjusts future questions based on user performance. Over time, Sophi builds a deep understanding of the class structure, content, and teaching style to deliver increasingly precise and effective practice.

## How we built it
Sophi is structured around a few core abstractions:

- **Session**: A single practice environment with configurable parameters.
- **Class**: A collection of *sessions* for a given course.
- **Class File (JSON)**: Custom-curated class metadata containing:
  - Topic breakdown (indented syllabus-style hierarchy)
  - Textbook citation (if applicable)
  - Style-notes derived from assignments (professor vocabulary, problem structure, common phrasing)

Additionally, Sophi leverages *RAG workflows* (leveraging FAISS vector-store databases) and *symbolic learning* (courtesy of Wolfram Alpha) to provide questions, hints, and answers grounded in real results.

The backend maintains session context across interactions, ensuring hints, feedback, and follow-ups are part of a continuous conversation rather than isolated prompts.

## Challenges we ran into
Karthik:

Max:

Joseph:


## Accomplishments that we're proud of

It was quite hard to brainstorm an idea for NexHacks - we wanted to do something big and unique, and attempt to contribute to a problem we all had firsthand experience with.

## What we learned


## What's next for Sophi


