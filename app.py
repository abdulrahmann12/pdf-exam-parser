# app.py

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import pdfplumber
import io
from typing import List, Dict, Any

app = FastAPI(
    title="Exam Question Parser",
    description="Upload a PDF or CSV file containing exam questions to parse them into JSON.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_QUESTION_TYPES = {"MCQ", "TRUE_FALSE"}
VALID_TRUE_FALSE_CHOICES = {"True", "False", "T", "F", "Yes", "No", "Y", "N"}


def parse_csv(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parse questions from a CSV file.
    Supported columns:
        - questionText
        - questionType (MCQ or TRUE_FALSE)
        - marks (e.g., 1, 2, ...)
        - choice1Text, choice1IsCorrect
        - choice2Text, choice2IsCorrect
        - choice3Text, choice3IsCorrect (optional)
        - choice4Text, choice4IsCorrect (optional)
    """
    df = pd.read_csv(io.BytesIO(file_bytes))
    questions = []
    for idx, row in df.iterrows():
        questionText = str(row.get("questionText", "")).strip()
        questionType = str(row.get("questionType", "")).strip()
        marks = int(row.get("marks", 1)) if not pd.isnull(row.get("marks")) else 1

        if questionType not in VALID_QUESTION_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid questionType on row {idx+1}")

        choices = []
        for i in range(1, 5):
            text_col = f"choice{i}Text"
            correct_col = f"choice{i}IsCorrect"
            choice_text = row.get(text_col)
            is_correct = row.get(correct_col)

            # Stop at the first missing choice text for MCQs
            if pd.isnull(choice_text):
                continue
            if isinstance(is_correct, str):
                is_correct = is_correct.strip().lower() in ("yes", "true", "t", "1")
            else:
                is_correct = bool(is_correct)

            choices.append({
                "choiceText": str(choice_text).strip(),
                "isCorrect": is_correct,
                "choiceOrder": len(choices) + 1
            })

        question = {
            "questionText": questionText,
            "questionType": questionType,
            "questionOrder": idx + 1,
            "marks": marks,
            "choices": choices
        }
        questions.append(question)
    return questions


def parse_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parse questions from a PDF file.
    Expected PDF format:
      Each question block follows this pattern, separated by blank lines:
        Q: Question text
        Type: MCQ or TRUE_FALSE
        Marks: <int>
        Choices:
        1. Choice text [* if correct]
        2. Choice text [* if correct]
        ...
    Example:
        Q: The largest planet?
        Type: MCQ
        Marks: 3
        Choices:
        1. Mars
        2. Jupiter *
        3. Saturn

        Q: The sun rises from the east.
        Type: TRUE_FALSE
        Marks: 1
        Choices:
        1. True *
        2. False
    """
    questions = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        full_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    lines = full_text.strip().splitlines()

    # Helper to build a question dict from accumulated state
    def _flush(q_text, q_type, q_marks, q_choices, q_order):
        if q_text or q_choices:
            questions.append({
                "questionText": q_text,
                "questionType": q_type,
                "questionOrder": q_order,
                "marks": q_marks,
                "choices": q_choices
            })

    questionText = ""
    questionType = ""
    marks = 1
    choices = []
    reading_choices = False
    order = 0

    for line in lines:
        line = line.strip()

        # Detect start of a new question block
        if line.lower().startswith("q:"):
            # Save previous question if any
            _flush(questionText, questionType, marks, choices, order)
            # Reset for new question
            order += 1
            questionText = line[2:].strip() if len(line) > 2 else ""
            questionType = ""
            marks = 1
            choices = []
            reading_choices = False
        elif line.lower().startswith("type:"):
            questionType = line[5:].strip().upper()
            reading_choices = False
        elif line.lower().startswith("marks:"):
            try:
                marks = int(line[6:].strip())
            except Exception:
                marks = 1
            reading_choices = False
        elif line.lower().startswith("choices:"):
            reading_choices = True
        elif reading_choices and line and (line[0].isdigit() or line[0] == '-'):
            # E.g., "1. Option [*]"
            rest = line.split(".", 1)[1] if "." in line else line
            rest = rest.strip()
            is_correct = False
            if rest.endswith("*"):
                is_correct = True
                rest = rest[:-1].strip()
            choices.append({
                "choiceText": rest,
                "isCorrect": is_correct,
                "choiceOrder": len(choices) + 1
            })

    # Don't forget the last question
    _flush(questionText, questionType, marks, choices, order)
    return questions


def validate_questions(questions: List[Dict[str, Any]]) -> List[str]:
    """
    Run validation rules on parsed questions.
    Returns a list of error messages, empty if valid.
    """
    errors = []
    for idx, q in enumerate(questions):
        qt = q.get("questionType")
        text = q.get("questionText", "").strip()
        choices = q.get("choices", [])
        mcq = qt == "MCQ"
        tf = qt == "TRUE_FALSE"

        # 1. Text required
        if not text:
            errors.append(f"Question {idx+1}: questionText is required.")

        # 2. Choices: at least 2 for true/false, 2-4 for MCQ
        if tf:
            if len(choices) != 2:
                errors.append(f"Question {idx+1} (TRUE_FALSE): exactly 2 choices required.")
            texts = {c["choiceText"].strip().lower() for c in choices}
            if not ({"true", "false"}.issubset(texts) or {"yes", "no"}.issubset(texts)):
                errors.append(f"Question {idx+1} (TRUE_FALSE): choices must be True/False or Yes/No.")
        elif mcq:
            if not (2 <= len(choices) <= 4):
                errors.append(f"Question {idx+1} (MCQ): 2-4 choices required.")

        # 3. At least one correct answer
        if not any(c.get("isCorrect") for c in choices):
            errors.append(f"Question {idx+1}: at least one correct choice is required.")
    return errors


@app.post("/parse-questions")
async def parse_questions(file: UploadFile = File(...)):
    """
    Accept an uploaded PDF or CSV and return standardized question JSON.
    """
    content = await file.read()
    filename = file.filename.lower()

    try:
        if filename.endswith(".csv"):
            questions = parse_csv(content)
        elif filename.endswith(".pdf"):
            questions = parse_pdf(content)
        else:
            raise HTTPException(status_code=400, detail="Only PDF or CSV files are supported.")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error parsing file: {str(e)}")

    errors = validate_questions(questions)
    if errors:
        return JSONResponse(content={"errors": errors}, status_code=422)
    return {"questions": questions}


# If running on Spaces, main will be handled by Hugging Face.
# Local run: uvicorn app:app --reload
# End Generation Here
