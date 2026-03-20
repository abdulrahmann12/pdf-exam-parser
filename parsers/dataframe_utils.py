"""Shared helper for converting a tabular DataFrame to the question list format."""

import logging
from typing import List, Dict, Any

import pandas as pd
from fastapi import HTTPException

logger = logging.getLogger(__name__)

VALID_QUESTION_TYPES = {"MCQ", "TRUE_FALSE"}
TRUE_VALUES = {"yes", "true", "t", "1"}


def dataframe_to_questions(df: pd.DataFrame) -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        question_text = str(row.get("questionText", "")).strip()
        question_type = str(row.get("questionType", "")).strip().upper()
        raw_marks = row.get("marks")
        marks = int(raw_marks) if not pd.isnull(raw_marks) else 1

        if question_type not in VALID_QUESTION_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid questionType '{question_type}' on row {idx + 1}",
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
