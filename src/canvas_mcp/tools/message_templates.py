"""Message templates for Canvas conversations."""

from typing import Any


class MessageTemplates:
    """Manages message templates for Canvas conversations."""

    # Default templates for peer review reminders
    PEER_REVIEW_TEMPLATES = {
        "urgent_no_reviews": {
            "subject": "URGENT: {assignment_name} Peer Review Deadline Approaching",
            "body": """Hi {student_name},

You have not yet completed any of your peer reviews for {assignment_name}.

You are assigned to review {total_assigned} submissions, and the deadline is approaching.

Please log into Canvas and complete your peer reviews as soon as possible:
{assignment_url}

If you have any questions or technical issues, please reach out immediately.

Best regards,
{instructor_name}"""
        },

        "partial_completion": {
            "subject": "Reminder: Complete Remaining Peer Review for {assignment_name}",
            "body": """Hi {student_name},

Great job completing {completed_count} of your peer reviews for {assignment_name}!

You still have {remaining_count} peer review remaining to complete:
{assignment_url}

Please complete this by the deadline to receive full participation credit.

Thanks,
{instructor_name}"""
        },

        "general_reminder": {
            "subject": "Peer Review Reminder: {assignment_name}",
            "body": """Hi {student_name},

This is a reminder about the peer reviews for {assignment_name}.

Please complete your assigned peer reviews by the deadline:
{assignment_url}

If you have any questions, please don't hesitate to ask.

Best regards,
{instructor_name}"""
        }
    }

    # Assignment reminder templates
    ASSIGNMENT_TEMPLATES = {
        "deadline_approaching": {
            "subject": "Reminder: {assignment_name} Due {deadline}",
            "body": """Hi {student_name},

This is a reminder that {assignment_name} is due {deadline}.

{assignment_description}

You can access the assignment here: {assignment_url}

Please submit your work before the deadline. If you have any questions or need assistance, please reach out.

Best regards,
{instructor_name}"""
        },

        "late_submission": {
            "subject": "Late Submission Notice: {assignment_name}",
            "body": """Hi {student_name},

Our records show that you have not yet submitted {assignment_name}, which was due {deadline}.

Please submit your work as soon as possible to minimize late penalties:
{assignment_url}

If you are experiencing technical difficulties or have extenuating circumstances, please contact me immediately.

Best regards,
{instructor_name}"""
        }
    }

    # Discussion participation templates
    DISCUSSION_TEMPLATES = {
        "participation_reminder": {
            "subject": "Discussion Participation Reminder: {discussion_title}",
            "body": """Hi {student_name},

I noticed you haven't participated in the discussion "{discussion_title}" yet.

Your participation is important for our class learning community. Please share your thoughts and engage with your classmates' posts:
{discussion_url}

The discussion closes {deadline}.

Looking forward to your contributions!

Best regards,
{instructor_name}"""
        }
    }

    # Grade notification templates
    GRADE_TEMPLATES = {
        "grade_available": {
            "subject": "Grade Available: {assignment_name}",
            "body": """Hi {student_name},

Your grade for {assignment_name} is now available in Canvas.

You can view your grade and feedback here: {assignment_url}

If you have any questions about your grade or the feedback provided, please don't hesitate to reach out.

Best regards,
{instructor_name}"""
        }
    }

    # Grading feedback templates - composable rubric-based feedback phrases
    GRADING_FEEDBACK_TEMPLATES = {
        "excellent": {
            "subject": "Excellent Work on {assignment_name}",
            "body": """{student_name} - Excellent work on {assignment_name}! Score: {score}/{max_score}.

{criterion_name}: Outstanding performance. Your work demonstrates thorough understanding and exceptional quality."""
        },
        "good": {
            "subject": "Good Work on {assignment_name}",
            "body": """{student_name} - Good work on {assignment_name}. Score: {score}/{max_score}.

{criterion_name}: Solid effort that meets expectations. Minor areas for improvement noted."""
        },
        "needs_improvement": {
            "subject": "Feedback on {assignment_name}",
            "body": """{student_name} - Score: {score}/{max_score} on {assignment_name}.

{criterion_name}: This area needs improvement. Please review the rubric criteria and consider revising your approach. Feel free to visit office hours to discuss strategies for strengthening this area."""
        },
        "missing": {
            "subject": "Missing Submission: {assignment_name}",
            "body": """{student_name} - You have not submitted {assignment_name}. Score: 0/{max_score}.

Please submit your work as soon as possible. If you are experiencing difficulties, reach out immediately so we can discuss options."""
        },
        "late_submission": {
            "subject": "Late Submission Graded: {assignment_name}",
            "body": """{student_name} - Your late submission for {assignment_name} has been graded. Score: {score}/{max_score}.

{criterion_name}: {feedback_comment}

Note: A late penalty may have been applied per the course late policy."""
        },
        "criterion_excellent": {
            "subject": "",
            "body": """{criterion_name}: Excellent ({score}/{max_score}). {feedback_comment}"""
        },
        "criterion_good": {
            "subject": "",
            "body": """{criterion_name}: Good ({score}/{max_score}). {feedback_comment}"""
        },
        "criterion_needs_work": {
            "subject": "",
            "body": """{criterion_name}: Needs improvement ({score}/{max_score}). {feedback_comment}"""
        },
        "criterion_missing": {
            "subject": "",
            "body": """{criterion_name}: Not addressed (0/{max_score}). This criterion was not met. Please review the rubric requirements."""
        }
    }

    @classmethod
    def compose_grading_feedback(
        cls,
        student_name: str,
        assignment_name: str,
        total_score: float,
        max_total: float,
        criterion_feedbacks: list[dict[str, Any]] | None = None
    ) -> str:
        """Compose a complete grading feedback comment from multiple criterion templates.

        Args:
            student_name: Student's display name
            assignment_name: Assignment title
            total_score: Total score awarded
            max_total: Maximum possible score
            criterion_feedbacks: List of dicts with keys:
                - criterion_name: Name of the criterion
                - score: Points awarded
                - max_score: Max points for criterion
                - level: "excellent", "good", "needs_work", or "missing"
                - comment: Optional additional comment

        Returns:
            Formatted feedback string combining all criterion feedback
        """
        # Determine overall level
        ratio = total_score / max_total if max_total > 0 else 0
        if ratio >= 0.9:
            overall_level = "excellent"
        elif ratio >= 0.7:
            overall_level = "good"
        elif total_score == 0:
            overall_level = "missing"
        else:
            overall_level = "needs_improvement"

        # Build header from overall template
        overall_template = cls.GRADING_FEEDBACK_TEMPLATES.get(overall_level, {})
        header = overall_template.get("body", "Score: {score}/{max_score}").format(
            student_name=student_name,
            assignment_name=assignment_name,
            score=total_score,
            max_score=max_total,
            criterion_name="Overall",
            feedback_comment=""
        ).strip()

        if not criterion_feedbacks:
            return header

        # Build criterion-level feedback
        parts = [header, ""]
        for cf in criterion_feedbacks:
            level = cf.get("level", "good")
            template_key = f"criterion_{level}"
            template = cls.GRADING_FEEDBACK_TEMPLATES.get(template_key, {})
            body = template.get("body", "{criterion_name}: {score}/{max_score}")

            formatted = body.format(
                criterion_name=cf.get("criterion_name", "Criterion"),
                score=cf.get("score", 0),
                max_score=cf.get("max_score", 0),
                feedback_comment=cf.get("comment", "")
            ).strip()
            parts.append(formatted)

        return "\n".join(parts)

    @classmethod
    def get_template(cls, category: str, template_name: str) -> dict[str, str] | None:
        """
        Get a specific template by category and name.

        Args:
            category: Template category (e.g., 'peer_review', 'assignment', 'grading_feedback')
            template_name: Specific template name within the category

        Returns:
            Template dict with 'subject' and 'body' keys, or None if not found
        """
        category_map = {
            "peer_review": cls.PEER_REVIEW_TEMPLATES,
            "assignment": cls.ASSIGNMENT_TEMPLATES,
            "discussion": cls.DISCUSSION_TEMPLATES,
            "grade": cls.GRADE_TEMPLATES,
            "grading_feedback": cls.GRADING_FEEDBACK_TEMPLATES
        }

        category_templates = category_map.get(category)
        if not category_templates:
            return None

        return category_templates.get(template_name)

    @classmethod
    def format_template(cls, template: dict[str, str], variables: dict[str, Any]) -> dict[str, str]:
        """
        Format a template with provided variables.

        Args:
            template: Template dict with 'subject' and 'body' keys
            variables: Variables to substitute in the template

        Returns:
            Formatted template with variables substituted
        """
        try:
            formatted_subject = template["subject"].format(**variables)
            formatted_body = template["body"].format(**variables)

            return {
                "subject": formatted_subject,
                "body": formatted_body
            }
        except KeyError as err:
            raise ValueError(f"Missing template variable: {err}") from err
        except Exception as err:
            raise ValueError(f"Template formatting error: {err}") from err

    @classmethod
    def get_formatted_template(
        cls,
        category: str,
        template_name: str,
        variables: dict[str, Any]
    ) -> dict[str, str] | None:
        """
        Get and format a template in one step.

        Args:
            category: Template category
            template_name: Template name
            variables: Variables for formatting

        Returns:
            Formatted template or None if template not found
        """
        template = cls.get_template(category, template_name)
        if not template:
            return None

        return cls.format_template(template, variables)

    @classmethod
    def list_available_templates(cls) -> dict[str, list]:
        """
        List all available templates by category.

        Returns:
            Dict mapping category names to lists of available template names
        """
        return {
            "peer_review": list(cls.PEER_REVIEW_TEMPLATES.keys()),
            "assignment": list(cls.ASSIGNMENT_TEMPLATES.keys()),
            "discussion": list(cls.DISCUSSION_TEMPLATES.keys()),
            "grade": list(cls.GRADE_TEMPLATES.keys()),
            "grading_feedback": list(cls.GRADING_FEEDBACK_TEMPLATES.keys())
        }

    @classmethod
    def get_template_variables(cls, category: str, template_name: str) -> list:
        """
        Get the variables used in a specific template.

        Args:
            category: Template category
            template_name: Template name

        Returns:
            List of variable names used in the template
        """
        template = cls.get_template(category, template_name)
        if not template:
            return []

        import re

        # Extract variables from both subject and body
        variables = set()
        for content in [template["subject"], template["body"]]:
            # Find all {variable_name} patterns
            matches = re.findall(r'\{([^}]+)\}', content)
            variables.update(matches)

        return sorted(variables)


def create_default_variables(
    student_name: str = "Student",
    assignment_name: str = "Assignment",
    instructor_name: str = "Instructor",
    course_name: str = "Course",
    **kwargs: Any
) -> dict[str, Any]:
    """
    Create a default set of template variables.

    Args:
        student_name: Student's display name
        assignment_name: Assignment title
        instructor_name: Instructor's name
        course_name: Course name
        **kwargs: Additional variables

    Returns:
        Dict of template variables
    """
    variables = {
        "student_name": student_name,
        "assignment_name": assignment_name,
        "instructor_name": instructor_name,
        "course_name": course_name,
        "assignment_url": "",
        "discussion_url": "",
        "deadline": "",
        "total_assigned": "2",
        "completed_count": "0",
        "remaining_count": "2",
        "assignment_description": ""
    }

    # Override with any provided kwargs
    variables.update(kwargs)

    return variables
