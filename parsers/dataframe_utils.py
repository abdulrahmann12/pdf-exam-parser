"""Shared helper for converting a tabular DataFrame to the question list format."""

import logging
from typing import List, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)

VALID_QUESTION_TYPES = {"MCQ", "TRUE_FALSE"}
TRUE_VALUES = {"yes", "true", "t", "1"}


def dataframe_to_questions(df: pd.DataFrame) -> List[Dict[str, Any]]:
    # Validate required columns exist
    required_columns = {"questionText", "questionType"}
    available_columns = set(df.columns)
    missing = required_columns - available_columns
    if missing:
        raise ValueError(
            f"Missing required column(s): {', '.join(sorted(missing))}. "
            f"Found columns: {', '.join(df.columns)}. "
            f"The file must contain at least these columns: questionText, questionType, marks, "
            f"choice1Text, choice1IsCorrect, choice2Text, choice2IsCorrect (up to choice4)."
        )

    # Check for choice columns
    has_any_choice = any(col.startswith("choice") and col.endswith("Text") for col in df.columns)
    if not has_any_choice:
        raise ValueError(
            f"No choice columns found. Found columns: {', '.join(df.columns)}. "
            f"The file must include at least 'choice1Text' and 'choice1IsCorrect' columns."
        )

    questions: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        row_num = idx + 1
        question_text = str(row.get("questionText", "")).strip()
        question_type = str(row.get("questionType", "")).strip().upper()

        raw_marks = row.get("marks")
        try:
            marks = int(raw_marks) if not pd.isnull(raw_marks) else 1
        except (ValueError, TypeError):
            logger.warning("Row %d: invalid marks value '%s', defaulting to 1", row_num, raw_marks)
            marks = 1

        if not question_text:
            raise ValueError(
                f"Row {row_num}: 'questionText' is empty or missing. Every row must contain the question text."
            )

        if not question_type:
            raise ValueError(
                f"Row {row_num}: 'questionType' is empty or missing. "
                f"Set it to one of: {', '.join(sorted(VALID_QUESTION_TYPES))}."
            )

        if question_type not in VALID_QUESTION_TYPES:
            raise ValueError(
                f"Row {row_num}: invalid questionType '{question_type}'. "
                f"Allowed values are: {', '.join(sorted(VALID_QUESTION_TYPES))}. "
                f"Check for typos or extra spaces in the 'questionType' column."
            )

        choices: List[Dict[str, Any]] = []
        for i in range(1, 5):
            choice_text = row.get(f"choice{i}Text")
            is_correct_raw = row.get(f"choice{i}IsCorrect")

            if pd.isnull(choice_text):
                continue

            if isinstance(is_correct_raw, str):
                is_correct = is_correct_raw.strip().lower() in TRUE_VALUES
            else:
                is_correct = bool(is_correct_raw) if not pd.isnull(is_correct_raw) else False

            choices.append({
                "choiceText": str(choice_text).strip(),
                "isCorrect": is_correct,
                "choiceOrder": len(choices) + 1,
            })

        questions.append({
            "questionText": question_text,
            "questionType": question_type,
            "questionOrder": idx + 1,
            "marks": marks,
            "choices": choices,
        })

    return questions
