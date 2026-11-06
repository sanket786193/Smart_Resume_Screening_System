"""AI Resume Parser extracting structured candidate data from documents and raw text."""
from __future__ import annotations

import re
from typing import Any, Dict, List
from ai.skill_extractor import skill_extractor
from ai.utils import deduplicate_preserve_order, normalize_text


class AIResumeParser:
    """Parses resumes into structured dictionaries containing all 11 core ATS entities."""

    def __init__(self) -> None:
        self.email_regex = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
        self.phone_regex = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
        self.github_regex = re.compile(r"(?:https?:\/\/)?(?:www\.)?github\.com\/([a-zA-Z0-9_-]+)", re.IGNORECASE)
        self.linkedin_regex = re.compile(r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/([a-zA-Z0-9_-]+)", re.IGNORECASE)

    def extract_name(self, text: str) -> str:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:5]:
            if len(line.split()) in (2, 3, 4) and not self.email_regex.search(line):
                cleaned = re.sub(r"[^a-zA-Z\s]", "", line).strip()
                if cleaned and len(cleaned.split()) >= 2:
                    return cleaned.title()
        return "Candidate"

    def extract_email(self, text: str) -> str:
        matches = self.email_regex.findall(text)
        return matches[0] if matches else ""

    def extract_phone(self, text: str) -> str:
        matches = self.phone_regex.findall(text)
        if matches:
            m = matches[0]
            return "".join(m) if isinstance(m, tuple) else m
        return ""

    def extract_github(self, text: str) -> str:
        matches = self.github_regex.findall(text)
        return f"https://github.com/{matches[0]}" if matches else ""

    def extract_linkedin(self, text: str) -> str:
        matches = self.linkedin_regex.findall(text)
        return f"https://linkedin.com/in/{matches[0]}" if matches else ""

    def extract_skills(self, text: str) -> List[str]:
        return skill_extractor.extract_skills_from_text(text)

    def extract_education(self, text: str) -> List[str]:
        degrees = [
            "Bachelor of Technology", "B.Tech", "B.E.", "Bachelor of Science", "B.S.", "B.Sc",
            "Master of Science", "M.S.", "M.Tech", "Master of Business Administration", "MBA",
            "Ph.D.", "Doctor of Philosophy", "Associate Degree", "High School Diploma"
        ]
        found = []
        for deg in degrees:
            pattern = re.compile(rf"\b{re.escape(deg)}\b", re.IGNORECASE)
            if pattern.search(text):
                found.append(deg)
        return deduplicate_preserve_order(found)

    def extract_experience_sections(self, text: str) -> List[Dict[str, Any]]:
        roles = [
            "Software Engineer", "Senior Software Engineer", "Full Stack Developer",
            "Backend Engineer", "Frontend Developer", "DevOps Engineer",
            "Data Scientist", "Machine Learning Engineer", "Cloud Architect",
            "Technical Lead", "Project Manager", "Product Manager", "QA Engineer"
        ]
        found_roles = []
        for role in roles:
            pattern = re.compile(rf"\b{re.escape(role)}\b", re.IGNORECASE)
            if pattern.search(text):
                found_roles.append(role)

        exp_pattern = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)(?:\s*of)?\s*(?:experience|exp)", re.IGNORECASE)
        matches = exp_pattern.findall(text)
        years = max([int(m) for m in matches]) if matches else len(found_roles) * 2

        return [{
            "roles": found_roles,
            "estimated_years": min(years, 30),
        }]

    def extract_projects(self, text: str) -> List[str]:
        projects = []
        proj_section = re.search(r"(?:projects|academic projects|key projects)([\s\S]*?)(?:education|experience|skills|certifications|$)", text, re.IGNORECASE)
        if proj_section:
            section_text = proj_section.group(1)
            lines = [l.strip("-•* \t") for l in section_text.split("\n") if len(l.strip()) > 15]
            projects.extend(lines[:5])
        return projects

    def extract_certifications(self, text: str) -> List[str]:
        certs = [
            "AWS Certified Solutions Architect", "AWS Certified Developer",
            "Google Cloud Certified Professional Cloud Architect", "Azure Fundamentals",
            "Certified Kubernetes Administrator (CKA)", "PMP", "Scrum Master (CSM)",
            "TensorFlow Developer Certificate", "Oracle Certified Professional"
        ]
        found = []
        for c in certs:
            if re.search(re.escape(c), text, re.IGNORECASE):
                found.append(c)
        return found

    def extract_languages(self, text: str) -> List[str]:
        common_langs = ["English", "Spanish", "French", "German", "Hindi", "Mandarin", "Japanese", "Portuguese"]
        found = []
        for lang in common_langs:
            if re.search(rf"\b{lang}\b", text, re.IGNORECASE):
                found.append(lang)
        return found or ["English"]

    def parse_text(self, text: str) -> Dict[str, Any]:
        norm = normalize_text(text)
        exp_info = self.extract_experience_sections(norm)
        years = exp_info[0]["estimated_years"] if exp_info else 0

        return {
            "name": self.extract_name(text),
            "email": self.extract_email(text),
            "phone": self.extract_phone(text),
            "github": self.extract_github(text),
            "linkedin": self.extract_linkedin(text),
            "skills": self.extract_skills(norm),
            "education": self.extract_education(norm),
            "experience_years": years,
            "experience_roles": exp_info[0]["roles"] if exp_info else [],
            "projects": self.extract_projects(text),
            "certifications": self.extract_certifications(norm),
            "languages": self.extract_languages(norm),
            "raw_text": text,
        }

    def parse_resume_instance(self, resume_instance: Any) -> Dict[str, Any]:
        """Extract structured entities from Resume model instance or fallback to text parsing."""
        raw_text = getattr(resume_instance, "raw_text", "") or ""

        # Check extracted attributes on Resume model
        ext_skills = getattr(resume_instance, "extracted_skills", None)
        if ext_skills and isinstance(ext_skills, list) and len(ext_skills) > 0:
            exp_list = getattr(resume_instance, "extracted_experience", [])
            years = len(exp_list) * 2 if exp_list else 3
            return {
                "name": getattr(resume_instance, "extracted_name", "") or self.extract_name(raw_text),
                "email": getattr(resume_instance, "extracted_email", "") or self.extract_email(raw_text),
                "phone": getattr(resume_instance, "extracted_phone", "") or self.extract_phone(raw_text),
                "github": getattr(resume_instance, "extracted_github", "") or self.extract_github(raw_text),
                "linkedin": getattr(resume_instance, "extracted_linkedin", "") or self.extract_linkedin(raw_text),
                "skills": ext_skills,
                "education": getattr(resume_instance, "extracted_education", []) or self.extract_education(raw_text),
                "experience_years": years,
                "experience_roles": exp_list,
                "projects": getattr(resume_instance, "extracted_projects", []) or self.extract_projects(raw_text),
                "certifications": getattr(resume_instance, "extracted_certifications", []) or self.extract_certifications(raw_text),
                "languages": getattr(resume_instance, "extracted_languages", []) or self.extract_languages(raw_text),
                "raw_text": raw_text,
            }

        return self.parse_text(raw_text)


# Singleton instance
ai_resume_parser = AIResumeParser()
