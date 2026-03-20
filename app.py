# app.py

import logging
from typing import List, Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from parsers import ParserResolver

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Exam Question Parser",
    description="Upload ANY file containing exam questions to parse them into JSON.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Parser resolver (singleton)
# ---------------------------------------------------------------------------
resolver = ParserResolver()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VALID_QUESTION_TYPES = {"MCQ", "TRUE_FALSE"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
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

        # 1. Text required
        if not text:
            errors.append(f"Question {idx+1}: questionText is required.")

        # 2. Choices: at least 2 for true/false, 2-4 for MCQ
        if qt == "TRUE_FALSE":
            if len(choices) != 2:
                errors.append(f"Question {idx+1} (TRUE_FALSE): exactly 2 choices required.")
            texts = {c["choiceText"].strip().lower() for c in choices}
            if not ({"true", "false"}.issubset(texts) or {"yes", "no"}.issubset(texts)):
                errors.append(f"Question {idx+1} (TRUE_FALSE): choices must be True/False or Yes/No.")
        elif qt == "MCQ":
            if not (2 <= len(choices) <= 4):
                errors.append(f"Question {idx+1} (MCQ): 2-4 choices required.")

        # 3. At least one correct answer
        if not any(c.get("isCorrect") for c in choices):
            errors.append(f"Question {idx+1}: at least one correct choice is required.")
    return errors


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@app.post("/parse-questions")
async def parse_questions(file: UploadFile = File(...)):
    """
    Accept ANY uploaded file, detect its type, parse it with the
    appropriate parser, validate, and return standardized question JSON.
    """
    content = await file.read()
    filename = file.filename or "unknown"
    content_type = file.content_type or "application/octet-stream"

    logger.info(
        "Received file: name='%s', content_type='%s', size=%d bytes",
        filename, content_type, len(content),
    )

    # Resolve the right parser
    parser = resolver.resolve(filename, content_type)
    parser_name = parser.__class__.__name__

    # Parse
    try:
        questions = parser.parse(content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Parser %s failed for '%s': %s", parser_name, filename, e)
        raise HTTPException(status_code=422, detail=f"Error parsing file: {str(e)}")

    logger.info(
        "Parsing complete: file='%s', parser=%s, questions_extracted=%d",
        filename, parser_name, len(questions),
    )

    # Validate
    errors = validate_questions(questions)
    if errors:
        return JSONResponse(content={"errors": errors}, status_code=422)

    return {"questions": questions}


# Local run: uvicorn app:app --reload
