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
    level=logging.DEBUG,
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
    try:
        content = await file.read()
    except Exception as e:
        logger.error("Failed to read uploaded file: %s", e, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Failed to read the uploaded file. The file may be corrupted or the upload was interrupted.",
        ) from e

    filename = file.filename or "unknown"
    content_type = file.content_type or "application/octet-stream"

    logger.info(
        "Received file: name='%s', content_type='%s', size=%d bytes",
        filename, content_type, len(content),
    )

    if not content:
        logger.warning("Empty file uploaded: '%s'", filename)
        raise HTTPException(
            status_code=400,
            detail=f"The uploaded file '{filename}' is empty. Please upload a file with content.",
        )

    # Resolve the right parser
    try:
        parser = resolver.resolve(filename, content_type)
    except ValueError as e:
        logger.error("No parser found for '%s' (content_type='%s'): %s", filename, content_type, e)
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: '{filename}' (content_type='{content_type}'). "
                   f"No suitable parser is available for this file format.",
        ) from e

    parser_name = parser.__class__.__name__

    # Parse
    try:
        questions = parser.parse(content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Parser %s failed for file '%s' (content_type='%s', size=%d bytes): %s",
            parser_name, filename, content_type, len(content), e, exc_info=True,
        )
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse '{filename}' using {parser_name}: {e}. "
                   f"Please verify the file is not corrupted and follows the expected format.",
        ) from e

    if not questions:
        logger.warning(
            "No questions extracted from '%s' using %s", filename, parser_name,
        )
        raise HTTPException(
            status_code=422,
            detail=f"No questions could be extracted from '{filename}'. "
                   f"Please ensure the file contains questions in the expected format.",
        )

    logger.info(
        "Parsing complete: file='%s', parser=%s, questions_extracted=%d",
        filename, parser_name, len(questions),
    )

    # Validate
    errors = validate_questions(questions)
    if errors:
        logger.warning("Validation failed for '%s': %s", filename, errors)
        return JSONResponse(content={"errors": errors}, status_code=422)

    return {"questions": questions}


# Local run: uvicorn app:app --reload
