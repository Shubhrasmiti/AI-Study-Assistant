
import json
import streamlit as st
from google import genai

st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="📚",
    layout="wide"
)

st.title("AI Study Notes & Question Generator")
st.write(
    "Generate study notes, review key concepts, "
    "and practise with an interactive quiz."
)
st.divider()

if "material" not in st.session_state:
    st.session_state.material = None

if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "quiz_attempt" not in st.session_state:
    st.session_state.quiz_attempt = 0   

with st.sidebar:
    st.header("Study Settings")
    level = st.selectbox(
        "Study level",
        ["School", "JEE/NEET", "College", "Competitive Exams"]
    )
    count = st.slider(
        "Number of questions",
        min_value=3,
        max_value=10,
        value=5
    )
st.subheader("Create Study Material")
topic = st.text_input(
    "Topic",
    placeholder="e.g. Database Normalization"
)
st.caption("Choose your study level and quiz length from the sidebar.")
if st.button("✨ Generate Study Material", type="primary"):
    if not topic.strip():
        st.warning("Please enter a topic first.")
    elif len(topic.strip()) < 3:
        st.warning("Please enter a more specific topic.")
    else:
        try:
            client = genai.Client(
                api_key=st.secrets["GEMINI_API_KEY"]
            )

            prompt = f"""
Create educational study material as valid JSON only.

Topic: {topic}
Student level: {level}
Number of questions: {count}

Use this exact JSON structure:
{{
  "title": "Topic title",
  "notes": "A clear explanation using Markdown formatting",
  "key_points": ["Important point 1", "Important point 2"],
  "terms": [
    {{"term": "Term", "definition": "Definition"}}
  ],
  "questions": [
    {{
      "question": "Question text",
      "options": {{
        "A": "Option one",
        "B": "Option two",
        "C": "Option three",
        "D": "Option four"
      }},
      "answer": "A",
      "explanation": "Why this answer is correct"
    }}
  ]
}}

Requirements:
- Generate exactly {count} questions.
- Every question must have four options labelled A, B, C, D.
- Each answer must be exactly one of A, B, C, D.
- Explanations must be accurate and useful.
- Keep the language appropriate for the student's level.
- Include key points and useful terms.
- Return valid JSON without Markdown code fences.
"""

            with st.spinner(
                "Generating material... this may take a few minutes."
            ):
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )

            if not response.text:
                raise ValueError("The AI returned an empty response.")

            material = json.loads(response.text)

            if not isinstance(material, dict):
                raise ValueError("The AI response has an invalid format.")

            if not material.get("questions"):
                raise ValueError("No quiz questions were generated.")

            if len(material["questions"]) != count:
                raise ValueError("The AI generated an unexpected number of questions.")

            for question in material["questions"]:
                if not all(key in question for key in
                        ["question", "options", "answer", "explanation"]):
                    raise ValueError("A question is missing required information.")

                if set(question["options"].keys()) != {"A", "B", "C", "D"}:
                    raise ValueError("A question does not have four valid options.")

                if question["answer"] not in {"A", "B", "C", "D"}:
                    raise ValueError("A question has an invalid answer.")

            st.session_state.material = material
            st.session_state.topic = topic
            st.session_state.quiz_submitted = False
            st.session_state.pop("quiz_answers", None)

        except Exception as e:
            st.error("Could not generate study material.")
            st.caption(f"Error details: {e}")

material = st.session_state.material

if material:
    study_text = f"# {material.get('title', 'Study Material')}\n\n"
    study_text += "## Study Notes\n\n"
    study_text += material.get("notes", "") + "\n\n"

    study_text += "## Key Points\n\n"
    for point in material.get("key_points", []):
        study_text += f"- {point}\n"

    study_text += "\n## Key Terms\n\n"
    for item in material.get("terms", []):
        study_text += f"- {item.get('term', '')}: {item.get('definition', '')}\n"

    study_text += "\n## Practice Quiz\n\n"
    for i, question in enumerate(material["questions"]):
        study_text += f"{i + 1}. {question['question']}\n"
        for key, option in question["options"].items():
            study_text += f"   {key}. {option}\n"
        study_text += "\n"

    study_text += "\n## Answer Key\n\n"
    for i, question in enumerate(material["questions"]):
        answer = question["answer"]
        study_text += f"{i + 1}. {answer}. {question['options'][answer]}\n"
        study_text += f"Explanation: {question['explanation']}\n\n"

    st.download_button(
        "📥 Download Study Material",
        data=study_text,
        file_name="study_material.md",
        mime="text/markdown"
    )


if material:
    st.divider()
    st.subheader(material.get("title", st.session_state.topic))

    notes_tab, quiz_tab, answers_tab = st.tabs(
        ["📘 Study Notes", "📝 Interactive Quiz", "✅ Answer Key"]
    )

    with notes_tab:
        st.markdown(material.get("notes", "No notes generated."))

        st.subheader("Key Points")
        for point in material.get("key_points", []):
            st.markdown(f"- {point}")

        st.subheader("Key Terms")
        for item in material.get("terms", []):
            st.markdown(
                f"**{item.get('term', 'Term')}:** "
                f"{item.get('definition', '')}"
            )

    with quiz_tab:
        st.write("Choose one answer for each question, then submit.")

        with st.form("quiz_form"):
            for i, question in enumerate(material["questions"]):
                st.markdown(
                    f"**Q{i + 1}. {question['question']}**"
                )

                options = question["options"]
                choice = st.radio(
                    f"Choose your answer for question {i + 1}",
                    options=list(options.keys()),
                    format_func=lambda key, opts=options:
                        f"{key}. {opts[key]}",
                    index=None,
                    key=f"question_{st.session_state.quiz_attempt}_{i}"
                )

                st.divider()

            submitted = st.form_submit_button("Submit Quiz")
            

        if submitted:
            unanswered = [
                i + 1
                for i in range(len(material["questions"]))
                if not st.session_state.get(
                    f"question_{st.session_state.quiz_attempt}_{i}"
                )
            ]

            if unanswered:
                st.warning(
                    "Please answer all questions before submitting. "
                    f"Unanswered: {', '.join(map(str, unanswered))}"
                )
            else:
                st.session_state.quiz_answers = {
                    str(i): st.session_state.get(
                        f"question_{st.session_state.quiz_attempt}_{i}"
                    )
                    for i in range(len(material["questions"]))
                }
                st.session_state.quiz_submitted = True

        if st.session_state.quiz_submitted:
            answers = st.session_state.quiz_answers
            score = sum(
                answers.get(str(i)) == q["answer"]
                for i, q in enumerate(material["questions"])
            )
            total = len(material["questions"])

            st.subheader(f"Your Score: {score}/{total}")
            st.progress(score / total if total else 0)
            if st.button("🔄 Try Again"):
                st.session_state.quiz_submitted = False
                st.session_state.pop("quiz_answers", None)
                st.session_state.quiz_attempt += 1
                st.rerun()

            if score == total:
                st.success("Excellent! You got every question right.")
            elif score >= total / 2:
                st.info("Good effort! Review the explanations to improve.")
            else:
                st.warning("Keep practising. Review the notes and try again.")

            for i, question in enumerate(material["questions"]):
                selected = answers.get(str(i))
                correct = question["answer"]

                st.markdown(f"**Q{i + 1}. {question['question']}**")

                if selected == correct:
                    st.success(f"Correct: {correct}. {question['options'][correct]}")
                else:
                    st.error(
                        f"Your answer: {selected or 'Not answered'}"
                    )
                    st.info(
                        f"Correct answer: {correct}. "
                        f"{question['options'][correct]}"
                    )

                st.write(question["explanation"])
                st.divider()

    with answers_tab:
        st.write("Use this section to review the correct answers.")
        for i, question in enumerate(material["questions"]):
            answer = question["answer"]
            st.markdown(f"**Q{i + 1}. {question['question']}**")
            st.write(f"**Answer: {answer}. {question['options'][answer]}**")
            st.write(question["explanation"])
            st.divider()

else:
    st.info("Enter a topic and click Generate Study Material to get started.")
