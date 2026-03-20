"""Shared helper for parsing the Q:/Type:/Marks:/Choices: text format."""

from typing import List, Dict, Any


def parse_text_block(text: str) -> List[Dict[str, Any]]:
    lines = text.strip().splitlines()
    questions: List[Dict[str, Any]] = []

    question_text = ""
    question_type = ""
    marks = 1
    choices: List[Dict[str, Any]] = []
    reading_choices = False
    order = 0

    def flush():
        nonlocal question_text, question_type, marks, choices, reading_choices
        if order > 0 and (question_text or choices):
            questions.append({
                "questionText": question_text,
                "questionType": question_type,
                "questionOrder": order,
                "marks": marks,
                "choices": list(choices),
            })

    for raw_line in lines:
        line = raw_line.strip()

        if line.lower().startswith("q:"):
            flush()
            order += 1
            question_text = line[2:].strip()
            question_type = ""
            marks = 1
            choices = []
            reading_choices = False

        elif line.lower().startswith("type:"):
            question_type = line[5:].strip().upper()
            reading_choices = False

        elif line.lower().startswith("marks:"):
            try:
                marks = int(line[6:].strip())
            except ValueError:
                marks = 1
            reading_choices = False

        elif line.lower().startswith("choices:"):
            reading_choices = True

        elif reading_choices and line and (line[0].isdigit() or line[0] == "-"):
            rest = line.split(".", 1)[1].strip() if "." in line else line
            is_correct = rest.endswith("*")
            if is_correct:
                rest = rest[:-1].strip()
            choices.append({
                "choiceText": rest,
                "isCorrect": is_correct,
                "choiceOrder": len(choices) + 1,
            })

    flush()
    return questions
