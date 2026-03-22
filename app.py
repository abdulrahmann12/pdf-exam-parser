# app.py

import logging
import traceback
from typing import List, Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
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
# Standardized error response helper
# ---------------------------------------------------------------------------
def error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: List[str] | None = None,
) -> JSONResponse:
    """Build a consistent JSON error response that callers can always parse."""
    body: Dict[str, Any] = {
        "success": False,
        "errorCode": error_code,
        "message": message,
    }
    if details:
        body["details"] = details
    return JSONResponse(content=body, status_code=status_code)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    """Wrap every HTTPException in the standard error envelope."""
    return error_response(
        status_code=exc.status_code,
        error_code="HTTP_ERROR",
        message=str(exc.detail),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_request: Request, exc: RequestValidationError):
    """Triggered when FastAPI cannot even validate the incoming request
    (e.g. missing file field)."""
    messages = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        messages.append(f"{loc}: {err.get('msg', 'invalid')}")
    return error_response(
        status_code=400,
        error_code="REQUEST_VALIDATION_ERROR",
        message="The request is invalid. Please check the required fields.",
        details=messages,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    """Catch-all so the caller never sees a raw 500 HTML page."""
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    return error_response(
        status_code=500,
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred while processing your request. Please try again or contact support.",
    )


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
        q_num = idx + 1
        qt = q.get("questionType")
        text = q.get("questionText", "").strip()
        choices = q.get("choices", [])

        # 1. questionType must be valid
        if not qt:
            errors.append(
                f"Question {q_num}: 'questionType' is missing. "
                f"Each question must have a type set to one of: {', '.join(sorted(VALID_QUESTION_TYPES))}."
            )
        elif qt not in VALID_QUESTION_TYPES:
            errors.append(
                f"Question {q_num}: invalid questionType '{qt}'. "
                f"Allowed values are: {', '.join(sorted(VALID_QUESTION_TYPES))}."
            )

        # 2. Text required
        if not text:
            errors.append(
                f"Question {q_num}: 'questionText' is empty or missing. "
                f"Every question must have text describing the question."
            )

        # 3. Choices validation per question type
        if qt == "TRUE_FALSE":
            if len(choices) != 2:
                errors.append(
                    f"Question {q_num} (TRUE_FALSE): must have exactly 2 choices, "
                    f"but found {len(choices)}. Provide exactly a True and a False choice."
                )
            if choices:
                texts = {c["choiceText"].strip().lower() for c in choices}
                if not ({"true", "false"}.issubset(texts) or {"yes", "no"}.issubset(texts)):
                    errors.append(
                        f"Question {q_num} (TRUE_FALSE): choices must be 'True'/'False' or 'Yes'/'No'. "
                        f"Found: {', '.join(c['choiceText'] for c in choices)}."
                    )
        elif qt == "MCQ":
            if len(choices) < 2:
                errors.append(
                    f"Question {q_num} (MCQ): must have at least 2 choices, but found {len(choices)}. "
                    f"Add more answer choices."
                )
            elif len(choices) > 4:
                errors.append(
                    f"Question {q_num} (MCQ): must have at most 4 choices, but found {len(choices)}. "
                    f"Remove extra choices so there are 2-4."
                )

        # 4. No choices at all
        if not choices:
            errors.append(
                f"Question {q_num}: no answer choices found. "
                f"Every question must have answer choices defined."
            )

        # 5. At least one correct answer
        elif not any(c.get("isCorrect") for c in choices):
            errors.append(
                f"Question {q_num}: no correct answer is marked. "
                f"You must set 'isCorrect' to true for at least one choice. "
                f"For CSV/Excel: set the 'choice1IsCorrect' (or choice2, choice3, choice4) column to 'true' for the correct answer. "
                f"For text files: add an asterisk (*) after the correct choice text."
            )

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
        return error_response(
            status_code=400,
            error_code="FILE_READ_ERROR",
            message=f"Failed to read the uploaded file. The file may be corrupted or the upload was interrupted.",
        )

    filename = file.filename or "unknown"
    content_type = file.content_type or "application/octet-stream"

    logger.info(
        "Received file: name='%s', content_type='%s', size=%d bytes",
        filename, content_type, len(content),
    )

    # --- Empty file ---
    if not content:
        logger.warning("Empty file uploaded: '%s'", filename)
        return error_response(
            status_code=400,
            error_code="EMPTY_FILE",
            message=f"The uploaded file '{filename}' is empty. Please upload a file that contains question data.",
        )

    # --- Resolve the right parser ---
    try:
        parser = resolver.resolve(filename, content_type)
    except ValueError as e:
        logger.error("No parser found for '%s' (content_type='%s'): %s", filename, content_type, e)
        return error_response(
            status_code=415,
            error_code="UNSUPPORTED_FILE_TYPE",
            message=(
                f"The file type of '{filename}' (content_type='{content_type}') is not supported. "
                f"Supported formats: PDF, CSV, Excel (.xlsx/.xls), Word (.docx), images (PNG/JPG), and plain text (.txt)."
            ),
        )

    parser_name = parser.__class__.__name__

    # --- Parse ---
    try:
        questions = parser.parse(content)
    except HTTPException as e:
        logger.error("Parser %s raised HTTPException for '%s': %s", parser_name, filename, e.detail)
        return error_response(
            status_code=e.status_code,
            error_code="PARSE_ERROR",
            message=str(e.detail),
        )
    except ValueError as e:
        logger.error("Parser %s raised ValueError for '%s': %s", parser_name, filename, e)
        return error_response(
            status_code=422,
            error_code="PARSE_ERROR",
            message=str(e),
        )
    except Exception as e:
        logger.error(
            "Parser %s failed unexpectedly for '%s' (content_type='%s', size=%d bytes): %s",
            parser_name, filename, content_type, len(content), e, exc_info=True,
        )
        return error_response(
            status_code=422,
            error_code="PARSE_ERROR",
            message=(
                f"Failed to parse '{filename}': {type(e).__name__}: {e}. "
                f"Please verify the file is not corrupted and follows the expected format."
            ),
        )

    # --- No questions found ---
    if not questions:
        logger.warning("No questions extracted from '%s' using %s", filename, parser_name)
        return error_response(
            status_code=422,
            error_code="NO_QUESTIONS_FOUND",
            message=(
                f"No questions could be extracted from '{filename}'. "
                f"For CSV/Excel: ensure columns are named 'questionText', 'questionType', 'choice1Text', 'choice1IsCorrect', etc. "
                f"For text/PDF/Word/Image: use the format Q: / Type: / Marks: / Choices: with numbered choices."
            ),
        )

    logger.info(
        "Parsing complete: file='%s', parser=%s, questions_extracted=%d",
        filename, parser_name, len(questions),
    )

    # --- Validate ---
    errors = validate_questions(questions)
    if errors:
        logger.warning("Validation failed for '%s': %s", filename, errors)
        return error_response(
            status_code=422,
            error_code="VALIDATION_ERROR",
            message=f"{len(errors)} validation error(s) found in '{filename}'. Please fix the issues below and re-upload.",
            details=errors,
        )

    return {"success": True, "questions": questions}


# Local run: uvicorn app:app --reload
