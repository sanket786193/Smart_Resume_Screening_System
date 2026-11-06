"""AI Recommendation Engine for candidate skill enhancement and resume optimization."""
from __future__ import annotations

from typing import Any, Dict, List


class RecommendationEngine:
    """Generates personalized action items, certification targets, and resume improvements."""

    CERTIFICATION_MAP: Dict[str, str] = {
        "AWS": "AWS Certified Solutions Architect - Associate",
        "Docker": "Docker Certified Associate (DCA)",
        "Kubernetes": "Certified Kubernetes Administrator (CKA)",
        "Python": "PCEP / PCAP Certified Associate Python Programmer",
        "Django": "Django Software Foundation Certification",
        "Security": "CompTIA Security+ / CEH",
        "Machine Learning": "Google Cloud Professional Machine Learning Engineer",
        "React": "Meta Certified Front-End Developer",
        "Scrum": "Professional Scrum Master (PSM I)",
    }

    PROJECT_TEMPLATES: Dict[str, str] = {
        "Docker": "Containerize a full-stack Django app with multi-stage Dockerfile and Docker Compose orchestration.",
        "Kubernetes": "Deploy a microservice cluster using Helm charts, Ingress controller, and automated horizontal pod autoscaling.",
        "Celery": "Implement asynchronous background report generation with Redis broker and Celery task queues.",
        "FastAPI": "Build high-throughput async microservices with automated OpenAPI docs and JWT authentication.",
        "Machine Learning": "Train and deploy a scikit-learn model with FastAPI endpoint and automated CI/CD unit testing.",
        "React": "Construct a responsive Single Page Application with React, Tailwind CSS, and state management.",
    }

    def generate_recommendations(
        self,
        resume_data: Dict[str, Any],
        job_data: Dict[str, Any],
        match_data: Dict[str, Any],
        ats_score_data: Dict[str, Any],
    ) -> List[str]:
        """Generate high-impact actionable advice for the candidate."""
        recommendations: List[str] = []
        missing_skills = match_data.get("missing_skills", [])
        raw_text = resume_data.get("raw_text", "")

        # 1. Missing Skills Suggestions
        if missing_skills:
            top_missing = missing_skills[:4]
            recommendations.append(
                f"Acquire or explicitly document these high-priority required skills: {', '.join(top_missing)}."
            )

        # 2. Certification Suggestions
        cert_recommendations = []
        for skill in missing_skills:
            if skill in self.CERTIFICATION_MAP:
                cert_recommendations.append(self.CERTIFICATION_MAP[skill])
        if cert_recommendations:
            recommendations.append(
                f"Boost ATS credibility with relevant certifications: {', '.join(cert_recommendations[:2])}."
            )

        # 3. Project Suggestions
        proj_recommendations = []
        for skill in missing_skills:
            if skill in self.PROJECT_TEMPLATES:
                proj_recommendations.append(self.PROJECT_TEMPLATES[skill])
        if proj_recommendations:
            recommendations.append(
                f"Demonstrate applied competency with this portfolio project: {proj_recommendations[0]}"
            )

        # 4. Resume Formatting & Impact improvements
        has_metrics = bool(re_search := any(char.isdigit() for char in raw_text))
        if not has_metrics or len(resume_data.get("projects", [])) < 2:
            recommendations.append(
                "Quantify bullet points with measurable impact (e.g. 'Improved API response latency by 35%')."
            )

        if not resume_data.get("github"):
            recommendations.append(
                "Include a public GitHub profile with active code repositories to validate practical engineering ability."
            )

        if not resume_data.get("linkedin"):
            recommendations.append(
                "Add an updated LinkedIn profile link to enhance recruiter verification."
            )

        return recommendations


# Singleton instance
recommendation_engine = RecommendationEngine()

