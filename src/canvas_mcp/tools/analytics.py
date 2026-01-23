"""Course analytics MCP tools for Canvas API.

Provides teacher-facing analytics tools for monitoring student engagement,
course activity, assignment statistics, and generating reports.
"""

from mcp.server.fastmcp import FastMCP

from ..core.cache import get_course_code, get_course_id
from ..core.client import fetch_all_paginated_results, make_canvas_request
from ..core.dates import format_date
from ..core.validation import validate_params


def register_analytics_tools(mcp: FastMCP):
    """Register all course analytics MCP tools."""

    @mcp.tool()
    @validate_params
    async def get_course_student_summaries(
        course_identifier: str | int,
        sort_by: str = "name"
    ) -> str:
        """Get per-student engagement metrics for a course.

        Returns student count, engagement levels, tardiness summary,
        and identifies students who may need attention.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            sort_by: Sort order for results. Options: name, name_descending,
                     score, score_descending, participations, participations_descending,
                     page_views, page_views_descending
        """
        course_id = await get_course_id(course_identifier)

        # Validate sort_by parameter
        valid_sort_options = [
            "name", "name_descending",
            "score", "score_descending",
            "participations", "participations_descending",
            "page_views", "page_views_descending"
        ]
        if sort_by not in valid_sort_options:
            return f"Error: Invalid sort_by option '{sort_by}'. Valid options: {', '.join(valid_sort_options)}"

        params = {
            "sort_column": sort_by.replace("_descending", ""),
            "per_page": 100
        }
        if sort_by.endswith("_descending"):
            params["sort_order"] = "descending"

        students = await fetch_all_paginated_results(
            f"/courses/{course_id}/analytics/student_summaries",
            params
        )

        if isinstance(students, dict) and "error" in students:
            return f"Error fetching student summaries: {students['error']}"

        if not students:
            return "No student analytics data available for this course."

        # Calculate summary statistics
        total_students = len(students)
        total_page_views = sum(s.get("page_views", 0) or 0 for s in students)
        total_participations = sum(s.get("participations", 0) or 0 for s in students)

        # Identify engagement levels
        no_activity = []
        low_engagement = []
        high_tardiness = []

        for student in students:
            page_views = student.get("page_views", 0) or 0
            participations = student.get("participations", 0) or 0
            tardiness = student.get("tardiness_breakdown", {})
            late_count = tardiness.get("late", 0) or 0
            missing_count = tardiness.get("missing", 0) or 0

            student_name = student.get("name", f"Student {student.get('id', 'Unknown')}")

            if page_views == 0 and participations == 0:
                no_activity.append(student_name)
            elif page_views < 10 and participations < 5:
                low_engagement.append(student_name)

            if missing_count > 2 or late_count > 3:
                high_tardiness.append({
                    "name": student_name,
                    "late": late_count,
                    "missing": missing_count
                })

        # Build summary report
        course_display = await get_course_code(course_id) or course_identifier
        lines = [
            f"Student Analytics Summary for {course_display}",
            "=" * 50,
            "",
            f"Total Students: {total_students}",
            f"Total Page Views: {total_page_views}",
            f"Total Participations: {total_participations}",
            f"Average Page Views per Student: {total_page_views / total_students:.1f}" if total_students > 0 else "",
            f"Average Participations per Student: {total_participations / total_students:.1f}" if total_students > 0 else "",
            ""
        ]

        # Students needing attention
        if no_activity:
            lines.append(f"⚠️ Students with No Activity ({len(no_activity)}):")
            for name in no_activity[:10]:
                lines.append(f"  - {name}")
            if len(no_activity) > 10:
                lines.append(f"  ... and {len(no_activity) - 10} more")
            lines.append("")

        if low_engagement:
            lines.append(f"📉 Students with Low Engagement ({len(low_engagement)}):")
            for name in low_engagement[:10]:
                lines.append(f"  - {name}")
            if len(low_engagement) > 10:
                lines.append(f"  ... and {len(low_engagement) - 10} more")
            lines.append("")

        if high_tardiness:
            lines.append(f"⏰ Students with Tardiness Issues ({len(high_tardiness)}):")
            for s in high_tardiness[:10]:
                lines.append(f"  - {s['name']}: {s['late']} late, {s['missing']} missing")
            if len(high_tardiness) > 10:
                lines.append(f"  ... and {len(high_tardiness) - 10} more")
            lines.append("")

        # Top engaged students (first 5 by current sort)
        if students:
            lines.append("Top 5 Students by Current Sort:")
            for student in students[:5]:
                name = student.get("name", f"Student {student.get('id', 'Unknown')}")
                pv = student.get("page_views", 0) or 0
                part = student.get("participations", 0) or 0
                lines.append(f"  - {name}: {pv} views, {part} participations")

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def get_student_activity(
        course_identifier: str | int,
        student_id: str | int
    ) -> str:
        """Get hourly page views and participation data for a specific student.

        Returns weekly summary, peak activity times, and recent participation events.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            student_id: The student's Canvas user ID
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/analytics/users/{student_id}/activity"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching student activity: {response['error']}"

        if not response:
            return "No activity data available for this student."

        # Process page views by day
        page_views = response.get("page_views", {})
        participations = response.get("participations", [])

        # Summarize page views
        total_views = 0
        view_by_day = {}

        if isinstance(page_views, dict):
            for date_str, count in page_views.items():
                if count:
                    total_views += count
                    # Extract day of week from date
                    try:
                        from datetime import datetime
                        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        day_name = date_obj.strftime("%A")
                        view_by_day[day_name] = view_by_day.get(day_name, 0) + count
                    except (ValueError, TypeError):
                        pass

        # Process participations
        recent_participations = []
        if isinstance(participations, list):
            # Sort by created_at descending and take most recent
            sorted_parts = sorted(
                [p for p in participations if p.get("created_at")],
                key=lambda x: x.get("created_at", ""),
                reverse=True
            )
            for p in sorted_parts[:10]:
                created_at = format_date(p.get("created_at"))
                url = p.get("url", "")
                recent_participations.append({
                    "date": created_at,
                    "url": url
                })

        course_display = await get_course_code(course_id) or course_identifier
        lines = [
            f"Student Activity for Course {course_display}",
            "=" * 50,
            "",
            f"Total Page Views: {total_views}",
            f"Total Participations: {len(participations) if isinstance(participations, list) else 0}",
            ""
        ]

        if view_by_day:
            lines.append("Page Views by Day of Week:")
            # Sort by view count
            for day, count in sorted(view_by_day.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {day}: {count}")
            lines.append("")

            # Find peak activity day
            if view_by_day:
                peak_day = max(view_by_day.keys(), key=lambda d: view_by_day[d])
                lines.append(f"📊 Peak Activity Day: {peak_day}")
                lines.append("")

        if recent_participations:
            lines.append("Recent Participations (last 10):")
            for p in recent_participations:
                url_short = p["url"][:50] + "..." if len(p["url"]) > 50 else p["url"]
                lines.append(f"  - {p['date']}: {url_short}")
        else:
            lines.append("No recent participations recorded.")

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def get_student_assignment_data(
        course_identifier: str | int,
        student_id: str | int
    ) -> str:
        """Get per-assignment grades and submission data for a specific student.

        Returns assignment scores, submission status, and grade trends.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            student_id: The student's Canvas user ID
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/analytics/users/{student_id}/assignments"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching student assignments: {response['error']}"

        if not response or not isinstance(response, list):
            return "No assignment analytics data available for this student."

        # Process assignments
        total_points_possible = 0
        total_points_earned = 0
        submitted_count = 0
        missing_count = 0
        late_count = 0

        assignments_info = []

        for assignment in response:
            title = assignment.get("title", "Untitled")
            points_possible = assignment.get("points_possible", 0) or 0
            submission = assignment.get("submission", {})

            if submission:
                score = submission.get("score")
                submitted_at = submission.get("submitted_at")
                late = submission.get("late", False)

                if score is not None:
                    total_points_earned += score
                    total_points_possible += points_possible
                    submitted_count += 1

                    status = "✓"
                    if late:
                        status = "⚠️ Late"
                        late_count += 1

                    assignments_info.append({
                        "title": title,
                        "score": f"{score}/{points_possible}",
                        "percent": f"{(score/points_possible*100):.1f}%" if points_possible > 0 else "N/A",
                        "status": status,
                        "submitted_at": format_date(submitted_at)
                    })
                elif submitted_at:
                    submitted_count += 1
                    assignments_info.append({
                        "title": title,
                        "score": "Pending",
                        "percent": "N/A",
                        "status": "Submitted",
                        "submitted_at": format_date(submitted_at)
                    })
                else:
                    missing_count += 1
                    assignments_info.append({
                        "title": title,
                        "score": "---",
                        "percent": "N/A",
                        "status": "❌ Missing",
                        "submitted_at": "N/A"
                    })
            else:
                missing_count += 1
                assignments_info.append({
                    "title": title,
                    "score": "---",
                    "percent": "N/A",
                    "status": "❌ Missing",
                    "submitted_at": "N/A"
                })

        # Calculate overall grade
        overall_percent = (total_points_earned / total_points_possible * 100) if total_points_possible > 0 else 0

        course_display = await get_course_code(course_id) or course_identifier
        lines = [
            f"Student Assignment Analytics for {course_display}",
            "=" * 50,
            "",
            f"Total Assignments: {len(response)}",
            f"Submitted: {submitted_count}",
            f"Missing: {missing_count}",
            f"Late: {late_count}",
            "",
            f"📊 Overall Grade: {total_points_earned:.1f}/{total_points_possible:.1f} ({overall_percent:.1f}%)",
            "",
            "Assignment Details:",
            "-" * 40
        ]

        for a in assignments_info:
            title_short = a["title"][:30] + "..." if len(a["title"]) > 30 else a["title"]
            lines.append(f"  {title_short}")
            lines.append(f"    Score: {a['score']} ({a['percent']}) {a['status']}")
            if a["submitted_at"] != "N/A":
                lines.append(f"    Submitted: {a['submitted_at']}")
            lines.append("")

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def get_student_communication(
        course_identifier: str | int,
        student_id: str | int
    ) -> str:
        """Get messaging metrics between a student and the instructor.

        Returns message counts and communication summary.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            student_id: The student's Canvas user ID
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/analytics/users/{student_id}/communication"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching student communication: {response['error']}"

        if not response:
            return "No communication data available for this student."

        # Extract message data
        message_data = response.get("level", {}) if isinstance(response, dict) else {}
        instructor_messages = message_data.get("instructorMessages", 0) or 0
        student_messages = message_data.get("studentMessages", 0) or 0

        course_display = await get_course_code(course_id) or course_identifier
        lines = [
            f"Student Communication Analytics for {course_display}",
            "=" * 50,
            "",
            f"Messages from Instructor: {instructor_messages}",
            f"Messages from Student: {student_messages}",
            f"Total Messages: {instructor_messages + student_messages}",
            ""
        ]

        # Add communication assessment
        if instructor_messages == 0 and student_messages == 0:
            lines.append("📭 No direct messaging communication recorded.")
        elif student_messages > instructor_messages * 2:
            lines.append("📨 Student is highly communicative.")
        elif instructor_messages > student_messages * 2:
            lines.append("📤 Instructor-initiated communication is dominant.")
        else:
            lines.append("✉️ Balanced communication between student and instructor.")

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def get_course_activity(
        course_identifier: str | int,
        start_date: str | None = None,
        end_date: str | None = None
    ) -> str:
        """Get daily course participation broken down by category.

        Returns activity by category (assignments, discussions, quizzes, etc.)
        and identifies peak activity days.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            start_date: Optional start date filter (ISO 8601 format, e.g., 2024-01-01)
            end_date: Optional end date filter (ISO 8601 format, e.g., 2024-12-31)
        """
        course_id = await get_course_id(course_identifier)

        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/analytics/activity",
            params=params if params else None
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching course activity: {response['error']}"

        if not response or not isinstance(response, list):
            return "No course activity data available."

        # Aggregate by category
        category_totals = {}
        daily_totals = []

        for day_data in response:
            date = day_data.get("date", "Unknown")
            day_total = 0

            for category, count in day_data.items():
                if category != "date" and isinstance(count, (int, float)):
                    category_totals[category] = category_totals.get(category, 0) + count
                    day_total += count

            daily_totals.append({"date": date, "total": day_total})

        # Sort daily totals to find peak days
        daily_totals.sort(key=lambda x: x["total"], reverse=True)

        total_activity = sum(category_totals.values())

        course_display = await get_course_code(course_id) or course_identifier
        lines = [
            f"Course Activity Analytics for {course_display}",
            "=" * 50,
            ""
        ]

        if start_date or end_date:
            date_range = f"{start_date or 'start'} to {end_date or 'present'}"
            lines.append(f"Date Range: {date_range}")
            lines.append("")

        lines.extend([
            f"Total Activity Events: {total_activity}",
            f"Days with Activity: {len([d for d in daily_totals if d['total'] > 0])}",
            ""
        ])

        if category_totals:
            lines.append("Activity by Category:")
            for category, count in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_activity * 100) if total_activity > 0 else 0
                lines.append(f"  {category}: {count} ({percentage:.1f}%)")
            lines.append("")

        if daily_totals:
            lines.append("Top 5 Peak Activity Days:")
            for day in daily_totals[:5]:
                if day["total"] > 0:
                    lines.append(f"  {day['date']}: {day['total']} events")
            lines.append("")

            # Most recent activity
            recent = sorted(
                [d for d in daily_totals if d["total"] > 0],
                key=lambda x: x["date"],
                reverse=True
            )
            if recent:
                lines.append(f"📅 Most Recent Activity: {recent[0]['date']} ({recent[0]['total']} events)")

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def get_assignment_statistics(
        course_identifier: str | int
    ) -> str:
        """Get grade distribution and timing statistics for all assignments.

        Returns per-assignment statistics including min/max/mean scores,
        submission counts, and late submission rates.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/analytics/assignments"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error fetching assignment statistics: {response['error']}"

        if not response or not isinstance(response, list):
            return "No assignment statistics available for this course."

        # Process assignments
        assignments_stats = []
        total_submissions = 0
        total_late = 0

        for assignment in response:
            title = assignment.get("title", "Untitled")
            points_possible = assignment.get("points_possible", 0)
            due_at = assignment.get("due_at")

            # Get statistics
            min_score = assignment.get("min_score")
            max_score = assignment.get("max_score")
            median = assignment.get("median")
            first_quartile = assignment.get("first_quartile")
            third_quartile = assignment.get("third_quartile")

            # Get tardiness info
            tardiness = assignment.get("tardiness_breakdown", {})
            on_time = tardiness.get("on_time", 0) or 0
            late = tardiness.get("late", 0) or 0
            missing = tardiness.get("missing", 0) or 0
            floating = tardiness.get("floating", 0) or 0

            total_for_assignment = on_time + late
            total_submissions += total_for_assignment
            total_late += late

            assignments_stats.append({
                "title": title,
                "points_possible": points_possible,
                "due_at": format_date(due_at),
                "min_score": min_score,
                "max_score": max_score,
                "median": median,
                "first_quartile": first_quartile,
                "third_quartile": third_quartile,
                "on_time": on_time,
                "late": late,
                "missing": missing,
                "floating": floating,
                "total_submitted": total_for_assignment
            })

        course_display = await get_course_code(course_id) or course_identifier
        lines = [
            f"Assignment Statistics for {course_display}",
            "=" * 50,
            "",
            f"Total Assignments: {len(assignments_stats)}",
            f"Total Submissions: {total_submissions}",
            f"Late Submissions: {total_late} ({total_late/total_submissions*100:.1f}%)" if total_submissions > 0 else "Late Submissions: 0",
            "",
            "Per-Assignment Breakdown:",
            "-" * 40
        ]

        for a in assignments_stats:
            title_short = a["title"][:35] + "..." if len(a["title"]) > 35 else a["title"]
            lines.append(f"\n📝 {title_short}")
            lines.append(f"   Points: {a['points_possible']} | Due: {a['due_at']}")

            if a["median"] is not None:
                lines.append(f"   Score Distribution:")
                lines.append(f"     Min: {a['min_score']:.1f} | Q1: {a['first_quartile']:.1f} | Median: {a['median']:.1f} | Q3: {a['third_quartile']:.1f} | Max: {a['max_score']:.1f}")
            else:
                lines.append("   Score Distribution: No graded submissions yet")

            lines.append(f"   Submissions: {a['total_submitted']} on-time: {a['on_time']} | late: {a['late']} | missing: {a['missing']}")

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def start_course_report(
        course_identifier: str | int,
        report_type: str
    ) -> str:
        """Start generating an asynchronous course report.

        Reports are generated in the background. Use get_report_status to check
        progress and retrieve the download URL when complete.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            report_type: Type of report to generate. Options:
                - grade_export_csv: Export all grades as CSV
                - student_assignment_outcome_map_csv: Student assignment outcomes
                - provisioning_csv: Provisioning data export
        """
        course_id = await get_course_id(course_identifier)

        # Validate report type
        valid_report_types = [
            "grade_export_csv",
            "student_assignment_outcome_map_csv",
            "provisioning_csv"
        ]
        if report_type not in valid_report_types:
            return f"Error: Invalid report type '{report_type}'. Valid options: {', '.join(valid_report_types)}"

        # Note: Course reports use a different endpoint structure
        # The /courses/{id}/reports endpoint allows starting reports
        response = await make_canvas_request(
            "post",
            f"/courses/{course_id}/reports/{report_type}"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error starting report: {response['error']}"

        if not response:
            return "Failed to start report - no response received."

        report_id = response.get("id")
        status = response.get("status", "unknown")
        progress = response.get("progress", 0)

        course_display = await get_course_code(course_id) or course_identifier
        lines = [
            f"Report Started for {course_display}",
            "=" * 50,
            "",
            f"Report Type: {report_type}",
            f"Report ID: {report_id}",
            f"Status: {status}",
            f"Progress: {progress}%",
            "",
            f"Use get_report_status('{course_identifier}', '{report_type}', {report_id}) to check progress.",
            "",
            "Note: Large reports may take several minutes to generate."
        ]

        return "\n".join(lines)

    @mcp.tool()
    @validate_params
    async def get_report_status(
        course_identifier: str | int,
        report_type: str,
        report_id: int
    ) -> str:
        """Check the status of a course report and get download URL when ready.

        Args:
            course_identifier: The Canvas course code (e.g., badm_554_120251_246794) or ID
            report_type: Type of report that was started
            report_id: The report ID returned from start_course_report
        """
        course_id = await get_course_id(course_identifier)

        response = await make_canvas_request(
            "get",
            f"/courses/{course_id}/reports/{report_type}/{report_id}"
        )

        if isinstance(response, dict) and "error" in response:
            return f"Error checking report status: {response['error']}"

        if not response:
            return "Failed to get report status - no response received."

        status = response.get("status", "unknown")
        progress = response.get("progress", 0)
        created_at = format_date(response.get("created_at"))
        attachment = response.get("attachment", {})

        course_display = await get_course_code(course_id) or course_identifier
        lines = [
            f"Report Status for {course_display}",
            "=" * 50,
            "",
            f"Report Type: {report_type}",
            f"Report ID: {report_id}",
            f"Status: {status}",
            f"Progress: {progress}%",
            f"Started: {created_at}",
            ""
        ]

        if status == "complete" and attachment:
            download_url = attachment.get("url", "")
            filename = attachment.get("filename", "report.csv")
            file_size = attachment.get("size", 0)

            lines.extend([
                "✅ Report Complete!",
                "",
                f"Filename: {filename}",
                f"Size: {file_size} bytes",
                f"Download URL: {download_url}",
                "",
                "Note: Download URLs expire after a short time."
            ])
        elif status == "running":
            lines.append("⏳ Report is still generating... Check back soon.")
        elif status == "error":
            message = response.get("message", "Unknown error")
            lines.extend([
                "❌ Report generation failed!",
                f"Error: {message}"
            ])
        else:
            lines.append(f"Current status: {status}")

        return "\n".join(lines)
