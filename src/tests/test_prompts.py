"""
Unit tests for backend/analyzer/prompts.py

Covers:
  - COMPLIANCE_QUESTIONS completeness
  - QUESTION_KEYWORDS coverage
  - COMPLIANCE_REQUIREMENTS coverage
  - Prompt template placeholders
"""

import pytest


def _import_prompts():
    from prompts import (
        COMPLIANCE_QUESTIONS, QUESTION_KEYWORDS,
        COMPLIANCE_REQUIREMENTS, SINGLE_Q_SYSTEM, SINGLE_Q_USER,
    )
    return COMPLIANCE_QUESTIONS, QUESTION_KEYWORDS, COMPLIANCE_REQUIREMENTS, SINGLE_Q_SYSTEM, SINGLE_Q_USER


class TestComplianceQuestions:
    def test_has_five_questions(self):
        questions = _import_prompts()[0]
        assert len(questions) == 5

    def test_expected_questions(self):
        questions = _import_prompts()[0]
        expected = {
            "Password Management",
            "IT Asset Management",
            "Security Training & Background Checks",
            "Data in Transit Encryption",
            "Network Authentication & Authorization Protocols",
        }
        assert set(questions) == expected


class TestQuestionKeywords:
    def test_all_questions_have_keywords(self):
        questions, keywords = _import_prompts()[:2]
        for q in questions:
            assert q in keywords, f"Missing keywords for '{q}'"
            assert len(keywords[q]) > 0, f"Empty keywords for '{q}'"

    def test_keywords_are_strings(self):
        keywords = _import_prompts()[1]
        for q, kws in keywords.items():
            for kw in kws:
                assert isinstance(kw, str)


class TestComplianceRequirements:
    def test_all_questions_have_requirements(self):
        questions, _, requirements = _import_prompts()[:3]
        for q in questions:
            assert q in requirements, f"Missing requirement for '{q}'"
            assert len(requirements[q]) > 50, f"Requirement too short for '{q}'"

    def test_requirements_mention_sub_requirements(self):
        requirements = _import_prompts()[2]
        for q, req in requirements.items():
            assert "Sub-requirements" in req or "sub-requirement" in req.lower()

    def test_requirements_mention_confidence_formula(self):
        requirements = _import_prompts()[2]
        for q, req in requirements.items():
            assert "confidence" in req.lower()


class TestPromptTemplates:
    def test_system_prompt_not_empty(self):
        system = _import_prompts()[3]
        assert len(system) > 100

    def test_system_prompt_mentions_json(self):
        system = _import_prompts()[3]
        assert "JSON" in system or "json" in system

    def test_user_template_has_placeholders(self):
        user = _import_prompts()[4]
        assert "{context}" in user
        assert "{requirement}" in user

    def test_user_template_formats(self):
        user = _import_prompts()[4]
        formatted = user.format(context="sample context", requirement="sample req")
        assert "sample context" in formatted
        assert "sample req" in formatted
