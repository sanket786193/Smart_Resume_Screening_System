"""
Intelligent Resume Information Extraction Engine.
Extracts Candidate Name, Contact, Skills, Education, Experience,
Projects, Certifications, Languages, and Social URLs.
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Common Canonical Skills dictionary for instantaneous matching
CANONICAL_SKILLS = [
    # Languages
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C", "Go", "Golang",
    "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "SQL", "HTML", "CSS", "Bash",
    # Frameworks & Libraries
    "Django", "Flask", "FastAPI", "React", "React.js", "Next.js", "Vue", "Vue.js",
    "Angular", "Spring Boot", "Express.js", "Node.js", "jQuery", "Bootstrap", "Tailwind CSS",
    "PyTorch", "TensorFlow", "Scikit-learn", "Keras", "Pandas", "NumPy", "OpenCV", "NLTK", "spaCy",
    # Databases & Storage
    "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Elasticsearch", "Cassandra", "DynamoDB",
    # Cloud & DevOps
    "AWS", "Amazon Web Services", "Azure", "Google Cloud", "GCP", "Docker", "Kubernetes",
    "CI/CD", "Jenkins", "GitHub Actions", "GitLab CI", "Terraform", "Ansible", "Linux", "Git",
    # Testing & Architecture
    "REST API", "GraphQL", "Microservices", "Unit Testing", "Pytest", "Selenium", "Agile", "Scrum",
]

COMMON_CERTIFICATIONS = [
    "AWS Certified Solutions Architect", "AWS Certified Developer", "AWS Certified Cloud Practitioner",
    "Google Cloud Certified Professional", "Azure Fundamentals", "Azure Solutions Architect",
    "Certified Kubernetes Administrator", "CKA", "CKAD", "PMP", "Project Management Professional",
    "Certified Scrum Master", "CSM", "CISSP", "CompTIA Security+", "CompTIA Network+",
]

COMMON_LANGUAGES = [
    "English", "Spanish", "French", "German", "Mandarin", "Chinese", "Hindi",
    "Arabic", "Russian", "Portuguese", "Japanese", "Italian", "Korean",
]

DEGREE_PATTERNS = [
    r"\b(?:Bachelor|B\.S\.|B\.A\.|B\.E\.|B\.Tech|BSc|BA|BTech|Undergraduate)\b[^\n]*",
    r"\b(?:Master|M\.S\.|M\.A\.|M\.E\.|M\.Tech|MSc|MA|MTech|Graduate)\b[^\n]*",
    r"\b(?:Doctorate|Ph\.D\.|PhD|Doctor of Philosophy)\b[^\n]*",
    r"\b(?:Associate Degree|Diploma|High School)\b[^\n]*",
]


class ResumeParser:
    """Parses raw resume textual corpus into structured semantic dictionary."""

    @classmethod
    def parse_text(cls, text: str) -> Dict[str, Any]:
        """Runs multi-pass heuristic and regex parsing on raw resume text."""
        result = {
            "name": cls.extract_name(text),
            "email": cls.extract_email(text),
            "phone": cls.extract_phone(text),
            "github": cls.extract_github(text),
            "linkedin": cls.extract_linkedin(text),
            "skills": cls.extract_skills(text),
            "education": cls.extract_education(text),
            "experience": cls.extract_experience(text),
            "projects": cls.extract_projects(text),
            "certifications": cls.extract_certifications(text),
            "languages": cls.extract_languages(text),
        }
        return result

    @staticmethod
    def extract_email(text: str) -> str:
        """Finds primary email address."""
        pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        match = re.search(pattern, text)
        return match.group(0).strip().lower() if match else ""

    @staticmethod
    def extract_phone(text: str) -> str:
        """Finds primary phone number."""
        pattern = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
        match = re.search(pattern, text)
        return match.group(0).strip() if match else ""

    @staticmethod
    def extract_github(text: str) -> str:
        """Finds GitHub profile URL."""
        pattern = r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9-_]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            username = match.group(1)
            return f"https://github.com/{username}"
        return ""

    @staticmethod
    def extract_linkedin(text: str) -> str:
        """Finds LinkedIn profile URL."""
        pattern = r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9-_]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            username = match.group(1)
            return f"https://linkedin.com/in/{username}"
        return ""

    @staticmethod
    def extract_name(text: str) -> str:
        """Heuristically extracts candidate name from header lines."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:5]:
            # Skip lines with emails, URLs, or labels
            if "@" in line or "http" in line or "www." in line or "github" in line or "resume" in line.lower():
                continue
            cleaned = re.sub(r"[^a-zA-Z\s]", "", line).strip()
            tokens = cleaned.split()
            if 2 <= len(tokens) <= 4:
                return cleaned.title()
        return ""

    @classmethod
    def extract_skills(cls, text: str) -> List[str]:
        """Matches canonical skills and dynamic database skills."""
        matched_skills = set()
        text_lower = f" {text.lower()} "

        # 1. Match from local canonical library
        for skill in CANONICAL_SKILLS:
            pattern = rf"(?<!\w){re.escape(skill.lower())}(?!\w)"
            if re.search(pattern, text_lower):
                matched_skills.add(skill)

        # 2. Check if jobs.Skill model exists and match dynamic skills
        try:
            from jobs.models import Skill
            for db_skill in Skill.objects.all():
                pattern = rf"(?<!\w){re.escape(db_skill.name.lower())}(?!\w)"
                if re.search(pattern, text_lower):
                    matched_skills.add(db_skill.name)
        except Exception:
            pass

        return sorted(list(matched_skills))

    @staticmethod
    def extract_education(text: str) -> List[str]:
        """Extracts degree and academic institution statements."""
        education_items = []
        for pattern in DEGREE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                cleaned = match.strip()[:100]
                if cleaned and cleaned not in education_items:
                    education_items.append(cleaned)
        return education_items[:4]

    @staticmethod
    def extract_experience(text: str) -> List[str]:
        """Extracts job titles and employment history fragments."""
        roles = [
            "Senior Software Engineer", "Software Engineer", "Backend Developer", "Frontend Developer",
            "Full Stack Developer", "DevOps Engineer", "Data Scientist", "Product Manager",
            "System Architect", "Team Lead", "Intern", "QA Engineer", "Cloud Architect",
        ]
        found_exp = []
        for role in roles:
            pattern = rf"\b{re.escape(role)}\b[^\n]*"
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                cleaned = m.strip()[:120]
                if cleaned and cleaned not in found_exp:
                    found_exp.append(cleaned)
        return found_exp[:5]

    @staticmethod
    def extract_projects(text: str) -> List[str]:
        """Identifies project headlines or GitHub linked repositories."""
        pattern = r"(?:Project|Initiative|System|Application)[:\s]+([^\n]{5,80})"
        matches = re.findall(pattern, text, re.IGNORECASE)
        cleaned = [m.strip() for m in matches if len(m.strip()) > 5]
        return list(dict.fromkeys(cleaned))[:4]

    @staticmethod
    def extract_certifications(text: str) -> List[str]:
        """Identifies verified certifications."""
        found = []
        for cert in COMMON_CERTIFICATIONS:
            if re.search(rf"\b{re.escape(cert)}\b", text, re.IGNORECASE):
                found.append(cert)
        return found

    @staticmethod
    def extract_languages(text: str) -> List[str]:
        """Identifies spoken/written natural languages."""
        found = []
        for lang in COMMON_LANGUAGES:
            if re.search(rf"\b{re.escape(lang)}\b", text, re.IGNORECASE):
                found.append(lang)
        return found
