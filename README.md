# $so\varphi$: the golden ratio of practice

$so\varphi$ / Sophi (pronounced *Sophie*), named after the word for *wisdom* in Greek, aims to bridge the gap between traditional practice tests and personalized, adaptive learning. By leveraging instructor-offered practice problems, Sophi not only adapts the difficulty and content to match the student's current level, but also ensures that the questions are aligned with the professor's teaching style. Through Sophi, students achieve the "golden ratio of practice" (get it? because $\varphi$), maximizing their efficiency and retention within their time constraints.

## External Tools / Libraries Used

*   **Frontend**: React, Material-UI
*   **Backend**: Flask, Python
*   **AI Utilities**: The Token Company API, Gemini API, Wolfram Alpha API

## Inspiration

In a world as futuristic as "Turing City," where AI is becoming increasingly sophisticated, we recognized the need for a tool that could promise a customizable education plan for each student, meeting them where they were at with as much practice as they needed. The exact level of intellectual stimulation required for each student to succeed is different, and we wanted to create a tool that could honor these differences, not letting resources be a barrier for each student to learn.

Sophi was inspired by the following problems:
*   Notoriously, most professors offer only two to three practice sets for each exam, leaving most students with no choice but to redo the homework and practice exams, or consult "non-canon" resources.
    *   As a result, students end up memorizing the answers to the practice problems, rather than understanding the underlying concepts. Studies (Roediger & Karpicke (2006)) show that this reduces performance by up to 20% in extreme scenarios.
*   As a student, we have little other choice than to view the practice solutions - there are currently no autonomous ways to check whether we're on the right track apart from a binary all or nothing response.
    *   Anderson, Corbett, Koedinger, and Pelletier (1995) found that students who received step-level hints instead of full solutions achieved learning gains about 10–20% higher on post-tests, showing that targeted hints are substantially more effective than simply revealing answers.
*   Finally, students get a random distribution of difficulty thrown at them when practicing, and often have trouble dialing in the exact skills they need to succeed.
    *   Dunlosky et al. (2013) found that students who rely on passive study methods such as rereading and highlighting—common but low-utility techniques—spend substantial time studying yet retain far less information over the long term, suggesting that a large portion of study time is effectively wasted when these ineffective strategies are used.

Each of us faced variations of this same set of problems in our first semester of college, with limited resources offered by professors in the interest of test integrity, and limited access to a one-on-one tutor when we needed it most, on those 3-AM crams before the final exam. While LLMs like ChatGPT, Claude, and Gemini are publically available and solid for about 85% of performance, they lack grounded knowledge of the class material and aren't built from the ground-up for the features we mention.

We know this market is saturated, but we pride ourselves on the ability to leverage LLMs and their unique propositions of customization to mimic instructor-style problem generation, while providing a hint generation pipeline deeply rooted in years of educational research.

## What it does
Sophi is an adaptive practice platform that generates personalized free-response questions tailored to a specific class. Its value propositions, designed to solve the three aforementioned problems, can be summarized as follows:
*   **Instructor-Curated Problems**: Sophi uses a proprietary pipeline to curate and generate questions in the same style as the instructor's practice sets, ensuring that the questions are aligned with the professor's teaching style and content.
*   **Adaptive Difficulty**: Sophi adapts the difficulty of the generated questions based on the student's performance, ensuring that the questions are just right for the student's current level of understanding.
*   **Personalized Hints**: Sophi provides various levels of personalized hints that are specific to the student's current level of understanding, helping them to navigate the problem-solving process more effectively.
*   **Continuous Adaptation**: Sophi continuously adapts the practice environment based on the student's performance, ensuring that the student is always receiving the most effective practice possible.

Users organize their coursework into **Classes**, each containing multiple **Sessions**—individual practice environments with configurable parameters like difficulty, topic focus, and adaptivity.

Each session dynamically generates questions, validates answers, provides targeted hints, explains mistakes, and adjusts future questions based on user performance. Over time, Sophi builds a deep understanding of the class structure, content, and teaching style to deliver increasingly precise and effective practice.

Each class stores a **Class File** (JSON) that contains custom-curated class metadata, including:
*   Topic breakdown (indented syllabus-style hierarchy)
*   Textbook citation (if applicable)
*   Style-notes derived from assignments (professor vocabulary, problem structure, common phrasing)=

Questions, hints, and answers are grounded in symbolic reasoning (courtesy of Wolfram Alpha) or 

This allows for Sophi to generate questions that are aligned with the professor's teaching style, provide hints that are specific to the student's current level of understanding, and ground the questions in the class material, ensuring that the questions are relevant and meaningful.

## How we built it

We divided our work into managing the frontend, backend, and AI utilities. As we had three people on our team, this allowed us to distribute the workload evenly, with each person focusing on a specific aspect of the project.

### Frontend

The frontend is a React application that provides a user-friendly interface for interacting with Sophi. It allows users to create and manage classes, sessions, and questions, as well as view and analyze their performance. We use Material-UI for styling and componentization, and React Router for client-side routing. 

### Backend

The backend is a Flask application that handles user authentication, class and session management, question generation, and interaction with the AI utilities. We use Flask-Login for user authentication, and Flask-SQLAlchemy for database management. Additionally, we leverage MongoDB for storing all Class File JSONs, as well as session-specific data like question history, performance metrics, and adaptivity parameters.

### AI Stack

We used Google Gemini Flash Lite 2.5 as the primary LLM for question generation and hint provision. Gemini 3 Flash is a state-of-the-art language model that is designed to be fast, efficient, and accurate, and our expansive prompting workflow allowed for robust results in near-real-time.

To mitigate hallucination, we utilize a combination of fact-checking mechanisms and post-processing filters. We leverage the Wolfram Alpha API and its use of symbolic learning, translating questions to a primitive form that allows for more accurate fact-checking. Additionally, we leverage entries from the textbook citation, retrieved via a FAISS Vector-Store database also hosted by MongoDB, to ensure that the generated questions are aligned with the class material.

We make a LOT of LLM calls :D. To allow for fast and succinct prompting, we leverage The Token Company and their `bear-1` model, which cuts redundant tokens. Surprisingly, we learned that `bear-1` does expansive pruning on LaTeX-oriented queries, yielding successful compressions which on average, yield higher-quality results. In total, we saved close to 40k tokens through our debugging process.

## Competitors

Again, we fully acknowledge that this space is extremely saturated, and that there are many other platforms that offer similar features. However, after careful market research, Sophi is the only service to offer stylistic customization of the generated questions, a feature of invaluable gain according to numerous research studies. The aforementioned studies reference the importance of a feature like this, citing a ~5.2% decrease in performance and a ~15% increase in time spent studying when students use resources apart from those of their own professor.

| Platform                                    | Instructor-Aligned Questions |  Adaptive Difficulty  |     Personalized Hints    | Style-Mimicking (Professor) | Continuous Student Model |
| ------------------------------------------- | :--------------------------: | :-------------------: | :-----------------------: | :-------------------------: | :----------------------: |
| **Sophi**                                   |              ✅              |           ✅          |             ✅            |              ✅             |            ✅            |
| **Quizlet AI**                              |               ❌              |   ⚠️ (topic tagging)  |             ❌             |              ❌              |  ⚠️ (progress tracking)  |
| **Khanmigo (Khan Academy)**                 |               ❌              | ✔️ (curriculum based) |        ✔️ (guided)        |              ❌              |            ✔️            |
| **Generic LLM Practice (ChatGPT / Gemini)** |               ❌              | ⚠️ (prompt-dependent) | ⚠️ (generic explanations) |              ❌              |             ❌            |


## About Us

Karthik: I am a current student researcher in the Teachable AI Lab at the Georgia Institute of Technology. I've worked over the past semester implementing nontraditional learning algorithms with a focus in symbolic learning, so I have a deep understanding of addressing the gap between LLM 

Max: 

Joseph: 

## Challenges and Accomplishments

It was quite hard to brainstorm an idea for NexHacks - we wanted to do something big and unique, and attempt to contribute to a problem we all had firsthand experience with.

Between the ripe hours of 1 AM and 3 AM, our team commenced the hardest integration we've all participated in. We had to work together to ensure that the frontend, backend, and AI utilities all worked seamlessly with each other. This was a challenge that we overcame with a lot of perseverance and collaboration.

This was the first hackathon where we came in with a well-refined idea. Our 

Needless to say, all of our team can agree that this is without a doubt the most difficult project we've ever worked on. However, we persevered and overcame all obstacles, and we're incredibly proud of the result, and we can all honestly say that with another week's worth of finetuning and perahps some 

## What we learned

Karthik: When I first embarked on this project, I was quite surprised by the amount of progress LLMs have made in the past three years. As a researcher leaning more on the traditional AI side, I was compelled by how old AI architecture design meshed with modern LLM solutions, resulting in strong and cohesive solutions. I'm also incredibly grateful for the various tools we had access to, especially The Token Company's models (which were so cool to use and inspect).

Max:

Joseph:


## What's next for Sophi

Sophi is far from finished. Our alpha iteration is strong and our value propositions stronger, but our hope is that Sophi can become a tool for both teachers and students. Most notably, our next steps are as follows:
*   **Instructor Admin:** Create a dashboard for instructors to manage their classes, view student progress, and adjust settings.
*   **Image / Voice Control:** Allow students to interact with the platform using images of their work thus far or voice commands, enhancing accessibility for those with disabilities and providing a more seamless, futuristic training setup.
*   **Proprietary Model Finetuning:** Finetune the proprietary model on a dataset of style transfer, allowing for more personalized and effective learning.
*   **Student Progress Tracking:** Implement a system for both students and teachers to track student progress per unit, allowing instructors to monitor individual students' performance and identify areas for improvement.
*   **Collaborative Learning:** Enable students to work together on assignments, fostering a sense of community and collaboration.

# Citations

*   Roediger, H. L., & Karpicke, J. D. (2006).  
    *Test-enhanced learning: Taking memory tests improves long-term retention.*  
    Psychological Science, 17(3), 249–255.  
    https://doi.org/10.1111/j.1467-9280.2006.01693.x

*   Anderson, J. R., Corbett, A. T., Koedinger, K. R., & Pelletier, R. (1995).  
    *Cognitive tutors: Lessons learned.*  
    The Journal of the Learning Sciences, 4(2), 167–207.  
    https://doi.org/10.1207/s15327809jls0402_2

*   Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., & Willingham, D. T. (2013).  
    *Improving students’ learning with effective learning techniques: Promising directions from cognitive and educational psychology.*  
    Psychological Science in the Public Interest, 14(1), 4–58.  
    https://doi.org/10.1177/1529100612453266
