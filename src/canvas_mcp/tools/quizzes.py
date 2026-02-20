"""Quiz management MCP tools for Canvas API (Classic Quizzes)."""

import json

from mcp.server.fastmcp import FastMCP

from ..core.cache import get_course_code, get_course_id
from ..core.client import fetch_all_paginated_results, make_canvas_request
from ..core.dates import format_date
from ..core.validation import validate_params


def register_quiz_tools(mcp: FastMCP) -> None:
    """Register quiz management MCP tools."""

    # ===== QUIZ CRUD =====

    @mcp.tool()
    @validate_params
    async def list_quizzes(
        course_identifier: str | int,
        search_term: str | None = None
    ) -> str:
        """List all quizzes for a course.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            search_term: Optional search term to filter quizzes by title
        """
        course_id = await get_course_id(course_identifier)

        params: dict = {"per_page": 100}
        if search_term:
            params["search_term"] = search_term

        quizzes = await fetch_all_paginated_results(
            f"/courses/{course_id}/quizzes", params
        )

        if isinstance(quizzes, dict) and "error" in quizzes:
            return f"Error fetching quizzes: {quizzes['error']}"

        if not quizzes or not isinstance(quizzes, list):
            return f"No quizzes found for course {course_identifier}."

        course_display = await get_course_code(course_id) or course_identifier
        result = f"Quizzes for Course {course_display}:\n\n"

        for q in quizzes:
            quiz_id = q.get("id")
            title = q.get("title", "Untitled")
            quiz_type = q.get("quiz_type", "assignment")
            points = q.get("points_possible", "N/A")
            published = "Published" if q.get("published") else "Unpublished"
            due_at = format_date(q.get("due_at"))
            time_limit = q.get("time_limit")
            question_count = q.get("question_count", 0)

            result += f"ID: {quiz_id} | {title}\n"
            result += f"  Type: {quiz_type} | Points: {points} | Questions: {question_count}\n"
            result += f"  Due: {due_at} | Status: {published}"
            if time_limit:
                result += f" | Time limit: {time_limit} min"
            result += "\n\n"

        return result

    @mcp.tool()
    @validate_params
    async def get_quiz_details(
        course_identifier: str | int,
        quiz_id: str | int
    ) -> str:
        """Get detailed information about a specific quiz.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            quiz_id: The Canvas quiz ID
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "get", f"/courses/{course_id}/quizzes/{quiz_id}"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching quiz details: {response['error']}"

        course_display = await get_course_code(course_id) or course_identifier

        result = f"Quiz Details for Course {course_display}:\n\n"
        result += f"Title: {response.get('title', 'Untitled')}\n"
        result += f"ID: {quiz_id}\n"
        result += f"Type: {response.get('quiz_type', 'N/A')}\n"
        result += f"Points Possible: {response.get('points_possible', 'N/A')}\n"
        result += f"Question Count: {response.get('question_count', 0)}\n"
        result += f"Published: {'Yes' if response.get('published') else 'No'}\n"
        result += f"Due: {format_date(response.get('due_at'))}\n"
        result += f"Unlock At: {format_date(response.get('unlock_at'))}\n"
        result += f"Lock At: {format_date(response.get('lock_at'))}\n"

        time_limit = response.get("time_limit")
        if time_limit:
            result += f"Time Limit: {time_limit} minutes\n"

        result += f"Allowed Attempts: {response.get('allowed_attempts', 1)}\n"
        result += f"Shuffle Answers: {'Yes' if response.get('shuffle_answers') else 'No'}\n"
        result += f"Show Correct Answers: {'Yes' if response.get('show_correct_answers') else 'No'}\n"
        result += f"One Question at a Time: {'Yes' if response.get('one_question_at_a_time') else 'No'}\n"

        description = response.get("description", "")
        if description:
            import re
            desc_clean = re.sub(r'<[^>]+>', '', description).strip()
            if len(desc_clean) > 500:
                desc_clean = desc_clean[:500] + "..."
            result += f"\nDescription:\n{desc_clean}\n"

        return result

    @mcp.tool()
    @validate_params
    async def create_quiz(
        course_identifier: str | int,
        title: str,
        quiz_type: str = "assignment",
        description: str | None = None,
        due_at: str | None = None,
        unlock_at: str | None = None,
        lock_at: str | None = None,
        time_limit: int | None = None,
        allowed_attempts: int = 1,
        points_possible: float | None = None,
        shuffle_answers: bool = False,
        show_correct_answers: bool = True,
        one_question_at_a_time: bool = False,
        published: bool = False
    ) -> str:
        """Create a new quiz in a course.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            title: Quiz title
            quiz_type: Type of quiz - "assignment", "practice_quiz", "graded_survey", or "survey"
            description: HTML description/instructions for the quiz
            due_at: Due date in ISO 8601 format
            unlock_at: When quiz becomes available (ISO 8601)
            lock_at: When quiz locks (ISO 8601)
            time_limit: Time limit in minutes (null for no limit)
            allowed_attempts: Number of allowed attempts (default: 1, -1 for unlimited)
            points_possible: Total points possible
            shuffle_answers: Shuffle answer choices (default: False)
            show_correct_answers: Show correct answers after submission (default: True)
            one_question_at_a_time: Show one question at a time (default: False)
            published: Whether to publish immediately (default: False for safety)
        """
        course_id = await get_course_id(course_identifier)

        data: dict = {
            "quiz": {
                "title": title,
                "quiz_type": quiz_type,
                "allowed_attempts": allowed_attempts,
                "shuffle_answers": shuffle_answers,
                "show_correct_answers": show_correct_answers,
                "one_question_at_a_time": one_question_at_a_time,
                "published": published
            }
        }

        if description:
            data["quiz"]["description"] = description
        if due_at:
            data["quiz"]["due_at"] = due_at
        if unlock_at:
            data["quiz"]["unlock_at"] = unlock_at
        if lock_at:
            data["quiz"]["lock_at"] = lock_at
        if time_limit is not None:
            data["quiz"]["time_limit"] = time_limit
        if points_possible is not None:
            data["quiz"]["points_possible"] = points_possible

        response = await make_canvas_request(
            "post", f"/courses/{course_id}/quizzes", data=data
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error creating quiz: {response['error']}"

        course_display = await get_course_code(course_id) or course_identifier
        new_id = response.get("id")
        result = f"Quiz created successfully in course {course_display}:\n\n"
        result += f"ID: {new_id}\n"
        result += f"Title: {response.get('title', title)}\n"
        result += f"Type: {response.get('quiz_type', quiz_type)}\n"
        result += f"Published: {'Yes' if response.get('published') else 'No'}\n"

        return result

    @mcp.tool()
    @validate_params
    async def update_quiz(
        course_identifier: str | int,
        quiz_id: str | int,
        title: str | None = None,
        description: str | None = None,
        quiz_type: str | None = None,
        due_at: str | None = None,
        unlock_at: str | None = None,
        lock_at: str | None = None,
        time_limit: int | None = None,
        allowed_attempts: int | None = None,
        points_possible: float | None = None,
        shuffle_answers: bool | None = None,
        show_correct_answers: bool | None = None,
        one_question_at_a_time: bool | None = None,
        published: bool | None = None
    ) -> str:
        """Update an existing quiz's settings.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            quiz_id: The Canvas quiz ID to update
            title: New title
            description: New HTML description
            quiz_type: New quiz type
            due_at: New due date (ISO 8601)
            unlock_at: New unlock date (ISO 8601)
            lock_at: New lock date (ISO 8601)
            time_limit: New time limit in minutes
            allowed_attempts: New allowed attempts
            points_possible: New points possible
            shuffle_answers: Shuffle answer choices
            show_correct_answers: Show correct answers after submission
            one_question_at_a_time: Show one question at a time
            published: Publish or unpublish the quiz
        """
        course_id = await get_course_id(course_identifier)

        quiz_data: dict = {}
        if title is not None:
            quiz_data["title"] = title
        if description is not None:
            quiz_data["description"] = description
        if quiz_type is not None:
            quiz_data["quiz_type"] = quiz_type
        if due_at is not None:
            quiz_data["due_at"] = due_at
        if unlock_at is not None:
            quiz_data["unlock_at"] = unlock_at
        if lock_at is not None:
            quiz_data["lock_at"] = lock_at
        if time_limit is not None:
            quiz_data["time_limit"] = time_limit
        if allowed_attempts is not None:
            quiz_data["allowed_attempts"] = allowed_attempts
        if points_possible is not None:
            quiz_data["points_possible"] = points_possible
        if shuffle_answers is not None:
            quiz_data["shuffle_answers"] = shuffle_answers
        if show_correct_answers is not None:
            quiz_data["show_correct_answers"] = show_correct_answers
        if one_question_at_a_time is not None:
            quiz_data["one_question_at_a_time"] = one_question_at_a_time
        if published is not None:
            quiz_data["published"] = published

        if not quiz_data:
            return "No update parameters provided."

        response = await make_canvas_request(
            "put", f"/courses/{course_id}/quizzes/{quiz_id}",
            data={"quiz": quiz_data}
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error updating quiz: {response['error']}"

        course_display = await get_course_code(course_id) or course_identifier
        return f"Quiz '{response.get('title', 'Unknown')}' (ID: {quiz_id}) updated successfully in course {course_display}."

    @mcp.tool()
    @validate_params
    async def delete_quiz(
        course_identifier: str | int,
        quiz_id: str | int
    ) -> str:
        """Delete a quiz from a course.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            quiz_id: The Canvas quiz ID to delete
        """
        course_id = await get_course_id(course_identifier)

        # Fetch details first for confirmation
        quiz = await make_canvas_request(
            "get", f"/courses/{course_id}/quizzes/{quiz_id}"
        )
        quiz_title = "Unknown"
        if isinstance(quiz, dict) and "error" not in quiz:
            quiz_title = quiz.get("title", "Unknown")

        response = await make_canvas_request(
            "delete", f"/courses/{course_id}/quizzes/{quiz_id}"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error deleting quiz: {response['error']}"

        course_display = await get_course_code(course_id) or course_identifier
        return f"Quiz '{quiz_title}' (ID: {quiz_id}) deleted from course {course_display}."

    @mcp.tool()
    @validate_params
    async def publish_quiz(
        course_identifier: str | int,
        quiz_id: str | int
    ) -> str:
        """Publish a quiz, making it available to students.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            quiz_id: The Canvas quiz ID to publish
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "put", f"/courses/{course_id}/quizzes/{quiz_id}",
            data={"quiz": {"published": True}}
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error publishing quiz: {response['error']}"

        course_display = await get_course_code(course_id) or course_identifier
        return f"Quiz '{response.get('title', 'Unknown')}' (ID: {quiz_id}) published in course {course_display}."

    @mcp.tool()
    @validate_params
    async def unpublish_quiz(
        course_identifier: str | int,
        quiz_id: str | int
    ) -> str:
        """Unpublish a quiz, hiding it from students.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            quiz_id: The Canvas quiz ID to unpublish
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "put", f"/courses/{course_id}/quizzes/{quiz_id}",
            data={"quiz": {"published": False}}
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error unpublishing quiz: {response['error']}"

        course_display = await get_course_code(course_id) or course_identifier
        return f"Quiz '{response.get('title', 'Unknown')}' (ID: {quiz_id}) unpublished in course {course_display}."

    # ===== QUIZ QUESTIONS =====

    @mcp.tool()
    @validate_params
    async def list_quiz_questions(
        course_identifier: str | int,
        quiz_id: str | int
    ) -> str:
        """List all questions in a quiz.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            quiz_id: The Canvas quiz ID
        """
        course_id = await get_course_id(course_identifier)

        questions = await fetch_all_paginated_results(
            f"/courses/{course_id}/quizzes/{quiz_id}/questions",
            {"per_page": 100}
        )

        if isinstance(questions, dict) and "error" in questions:
            return f"Error fetching quiz questions: {questions['error']}"

        if not questions or not isinstance(questions, list):
            return f"No questions found for quiz {quiz_id}."

        course_display = await get_course_code(course_id) or course_identifier
        result = f"Quiz Questions (Quiz ID: {quiz_id}) in {course_display}:\n\n"

        for i, q in enumerate(questions, 1):
            q_id = q.get("id")
            q_type = q.get("question_type", "unknown")
            q_text = q.get("question_text", "")
            points = q.get("points_possible", 0)
            position = q.get("position", i)

            # Clean HTML from question text
            import re
            text_clean = re.sub(r'<[^>]+>', '', q_text).strip()
            if len(text_clean) > 200:
                text_clean = text_clean[:200] + "..."

            result += f"Q{position}. [ID: {q_id}] ({q_type}, {points} pts)\n"
            result += f"   {text_clean}\n"

            # Show answer choices for applicable types
            answers = q.get("answers", [])
            if answers and q_type in ("multiple_choice_question", "true_false_question", "matching_question"):
                for ans in answers:
                    ans_text = ans.get("text", ans.get("html", ""))
                    if ans_text:
                        ans_clean = re.sub(r'<[^>]+>', '', str(ans_text)).strip()
                        result += f"     - {ans_clean}\n"

            result += "\n"

        return result

    @mcp.tool()
    @validate_params
    async def add_quiz_question(
        course_identifier: str | int,
        quiz_id: str | int,
        question_type: str,
        question_text: str,
        points_possible: float = 1.0,
        answers: str | None = None,
        position: int | None = None
    ) -> str:
        """Add a question to a quiz.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            quiz_id: The Canvas quiz ID
            question_type: Type of question - "multiple_choice_question", "true_false_question",
                "short_answer_question", "essay_question", "fill_in_multiple_blanks_question",
                "matching_question", "numerical_question"
            question_text: HTML text of the question
            points_possible: Points for the question (default: 1.0)
            answers: JSON array of answer objects. For multiple_choice: [{"text": "Answer", "weight": 100}]
                where weight=100 is correct, weight=0 is incorrect.
                For true_false: [{"text": "True", "weight": 100}, {"text": "False", "weight": 0}]
            position: Position of the question in the quiz
        """
        course_id = await get_course_id(course_identifier)

        question_data: dict = {
            "question_type": question_type,
            "question_text": question_text,
            "points_possible": points_possible
        }

        if answers:
            try:
                parsed_answers = json.loads(answers) if isinstance(answers, str) else answers
                question_data["answers"] = parsed_answers
            except json.JSONDecodeError:
                return "Error: 'answers' must be a valid JSON array."

        if position is not None:
            question_data["position"] = position

        response = await make_canvas_request(
            "post", f"/courses/{course_id}/quizzes/{quiz_id}/questions",
            data={"question": question_data}
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error adding question: {response['error']}"

        course_display = await get_course_code(course_id) or course_identifier
        new_id = response.get("id")
        return f"Question added to quiz {quiz_id} in course {course_display}:\n\n" \
               f"Question ID: {new_id}\n" \
               f"Type: {question_type}\n" \
               f"Points: {points_possible}"

    @mcp.tool()
    @validate_params
    async def update_quiz_question(
        course_identifier: str | int,
        quiz_id: str | int,
        question_id: str | int,
        question_text: str | None = None,
        question_type: str | None = None,
        points_possible: float | None = None,
        answers: str | None = None,
        position: int | None = None
    ) -> str:
        """Update an existing quiz question.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            quiz_id: The Canvas quiz ID
            question_id: The question ID to update
            question_text: New HTML text for the question
            question_type: New question type
            points_possible: New points value
            answers: New JSON array of answer objects
            position: New position in the quiz
        """
        course_id = await get_course_id(course_identifier)

        question_data: dict = {}
        if question_text is not None:
            question_data["question_text"] = question_text
        if question_type is not None:
            question_data["question_type"] = question_type
        if points_possible is not None:
            question_data["points_possible"] = points_possible
        if position is not None:
            question_data["position"] = position

        if answers is not None:
            try:
                parsed_answers = json.loads(answers) if isinstance(answers, str) else answers
                question_data["answers"] = parsed_answers
            except json.JSONDecodeError:
                return "Error: 'answers' must be a valid JSON array."

        if not question_data:
            return "No update parameters provided."

        response = await make_canvas_request(
            "put", f"/courses/{course_id}/quizzes/{quiz_id}/questions/{question_id}",
            data={"question": question_data}
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error updating question: {response['error']}"

        course_display = await get_course_code(course_id) or course_identifier
        return f"Question {question_id} updated in quiz {quiz_id} in course {course_display}."

    @mcp.tool()
    @validate_params
    async def delete_quiz_question(
        course_identifier: str | int,
        quiz_id: str | int,
        question_id: str | int
    ) -> str:
        """Delete a question from a quiz.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            quiz_id: The Canvas quiz ID
            question_id: The question ID to delete
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "delete", f"/courses/{course_id}/quizzes/{quiz_id}/questions/{question_id}"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error deleting question: {response['error']}"

        course_display = await get_course_code(course_id) or course_identifier
        return f"Question {question_id} deleted from quiz {quiz_id} in course {course_display}."

    # ===== QUIZ ANALYTICS =====

    @mcp.tool()
    @validate_params
    async def get_quiz_statistics(
        course_identifier: str | int,
        quiz_id: str | int
    ) -> str:
        """Get statistics and analytics for a quiz including average score and question analysis.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            quiz_id: The Canvas quiz ID
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "get", f"/courses/{course_id}/quizzes/{quiz_id}/statistics"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching quiz statistics: {response['error']}"

        course_display = await get_course_code(course_id) or course_identifier

        stats_list = response.get("quiz_statistics", [])
        if not stats_list:
            return f"No statistics available for quiz {quiz_id}."

        stats = stats_list[0] if stats_list else {}
        submission_stats = stats.get("submission_statistics", {})

        result = f"Quiz Statistics (Quiz ID: {quiz_id}) in {course_display}:\n\n"
        result += f"Submissions: {submission_stats.get('unique_count', 0)}\n"
        result += f"Average Score: {submission_stats.get('score_average', 'N/A')}\n"
        result += f"High Score: {submission_stats.get('score_high', 'N/A')}\n"
        result += f"Low Score: {submission_stats.get('score_low', 'N/A')}\n"
        result += f"Standard Deviation: {submission_stats.get('score_stdev', 'N/A')}\n"
        result += f"Duration Average: {submission_stats.get('duration_average', 'N/A')} sec\n\n"

        # Question statistics
        question_stats = stats.get("question_statistics", [])
        if question_stats:
            result += "Question Analysis:\n"
            for qs in question_stats:
                q_text = qs.get("question_text", "")
                import re
                text_clean = re.sub(r'<[^>]+>', '', q_text).strip()
                if len(text_clean) > 100:
                    text_clean = text_clean[:100] + "..."

                result += f"\n  Q: {text_clean}\n"
                result += f"  Correct: {qs.get('correct', 'N/A')} | "
                result += f"Incorrect: {qs.get('incorrect', 'N/A')} | "
                result += f"Partially Correct: {qs.get('partially_correct', 'N/A')}\n"

        return result

    @mcp.tool()
    @validate_params
    async def list_quiz_submissions(
        course_identifier: str | int,
        quiz_id: str | int
    ) -> str:
        """List all submissions for a quiz.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            quiz_id: The Canvas quiz ID
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "get", f"/courses/{course_id}/quizzes/{quiz_id}/submissions",
            params={"per_page": 100}
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching quiz submissions: {response['error']}"

        submissions = response.get("quiz_submissions", []) if isinstance(response, dict) else []

        if not submissions:
            return f"No submissions found for quiz {quiz_id}."

        course_display = await get_course_code(course_id) or course_identifier
        result = f"Quiz Submissions (Quiz ID: {quiz_id}) in {course_display}:\n\n"
        result += f"Total: {len(submissions)} submissions\n\n"

        for s in submissions:
            user_id = s.get("user_id")
            score = s.get("score", "N/A")
            kept_score = s.get("kept_score", "N/A")
            attempt = s.get("attempt", 1)
            workflow_state = s.get("workflow_state", "unknown")
            time_spent = s.get("time_spent")
            finished_at = format_date(s.get("finished_at"))

            result += f"User ID: {user_id} | Score: {score} | Kept: {kept_score}\n"
            result += f"  Attempt: {attempt} | Status: {workflow_state} | Finished: {finished_at}"
            if time_spent:
                minutes = time_spent // 60
                seconds = time_spent % 60
                result += f" | Time: {minutes}m {seconds}s"
            result += "\n\n"

        return result
