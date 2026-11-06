"""Skill extraction engine combining canonical dictionaries, regex boundaries, and RapidFuzz."""
from __future__ import annotations

import re
from typing import Dict, List, Set
from rapidfuzz import fuzz
from ai.utils import deduplicate_preserve_order

SKILL_TAXONOMY: Dict[str, List[str]] = {
    "Python": ["python", "python3", "py"],
    "Django": ["django", "django framework"],
    "Django REST Framework": ["django rest framework", "drf", "rest framework"],
    "FastAPI": ["fastapi", "fast api"],
    "Flask": ["flask"],
    "JavaScript": ["javascript", "js", "ecmascript"],
    "TypeScript": ["typescript", "ts"],
    "React": ["react", "react.js", "reactjs"],
    "Next.js": ["next.js", "nextjs", "next"],
    "Vue.js": ["vue", "vue.js", "vuejs"],
    "Angular": ["angular", "angularjs"],
    "Node.js": ["node.js", "nodejs", "node"],
    "Express.js": ["express", "express.js", "expressjs"],
    "HTML5": ["html", "html5"],
    "CSS3": ["css", "css3", "sass", "scss", "tailwind", "bootstrap"],
    "SQL": ["sql"],
    "PostgreSQL": ["postgresql", "postgres", "psql"],
    "MySQL": ["mysql"],
    "SQLite": ["sqlite", "sqlite3"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis", "redis cache"],
    "Docker": ["docker", "containerization"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda", "rds"],
    "Google Cloud Platform": ["gcp", "google cloud", "google cloud platform"],
    "Microsoft Azure": ["azure", "microsoft azure"],
    "Git": ["git", "github", "gitlab", "bitbucket"],
    "CI/CD": ["ci/cd", "continuous integration", "continuous deployment", "github actions", "jenkins"],
    "Linux": ["linux", "ubuntu", "debian", "bash", "shell scripting"],
    "REST API": ["rest", "rest api", "restful api", "restful services"],
    "GraphQL": ["graphql"],
    "Microservices": ["microservices", "microservice architecture"],
    "Celery": ["celery", "task queue", "background tasks"],
    "RabbitMQ": ["rabbitmq"],
    "Kafka": ["kafka", "apache kafka"],
    "Machine Learning": ["machine learning", "ml"],
    "Deep Learning": ["deep learning", "dl"],
    "Natural Language Processing": ["nlp", "natural language processing"],
    "Scikit-Learn": ["scikit-learn", "sklearn"],
    "TensorFlow": ["tensorflow", "tf"],
    "PyTorch": ["pytorch"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Computer Vision": ["computer vision", "opencv"],
    "spaCy": ["spacy"],
    "NLTK": ["nltk"],
    "PyTest": ["pytest", "unit testing", "tdd", "test driven development"],
    "Java": ["java", "spring", "spring boot"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "csharp", ".net", "dotnet"],
    "Go": ["golang", "go"],
    "Rust": ["rust"],
    "Agile": ["agile", "scrum", "kanban", "jira"],
    "System Design": ["software architecture", "system design", "scalability", "high availability"],
}


class SkillExtractor:
    """Robust extractor mapping text to canonical skills via exact regex and fuzzy matching."""

    def __init__(self) -> None:
        self.taxonomy = SKILL_TAXONOMY
        self._compiled_regexes = self._build_regex_cache()
        self._alias_map: Dict[str, str] = {}
        for canonical, aliases in self.taxonomy.items():
            self._alias_map[canonical.lower()] = canonical
            for alias in aliases:
                self._alias_map[alias.lower()] = canonical

    def _build_regex_cache(self) -> Dict[str, List[re.Pattern]]:
        compiled = {}
        for canonical, aliases in self.taxonomy.items():
            patterns = []
            for alias in aliases:
                escaped = re.escape(alias)
                pattern = re.compile(rf"(?:\b|\A){escaped}(?:\b|\Z)", re.IGNORECASE)
                patterns.append(pattern)
            compiled[canonical] = patterns
        return compiled

    def get_canonical(self, skill_name: str) -> str:
        """Resolve any alias or variation to its canonical title."""
        cleaned = skill_name.strip().lower()
        return self._alias_map.get(cleaned, skill_name.strip())

    def extract_skills_from_text(self, text: str | None) -> List[str]:
        if not text:
            return []
        
        extracted: Set[str] = set()
        text_lower = text.lower()

        for canonical, patterns in self._compiled_regexes.items():
            for p in patterns:
                if p.search(text_lower):
                    extracted.add(canonical)
                    break

        return sorted(list(extracted))

    def match_skill_fuzzy(self, skill_name: str, candidate_skills: List[str], threshold: float = 75.0) -> bool:
        """Check if skill_name matches any candidate skill by canonical equality or fuzzy token distance."""
        s_canon = self.get_canonical(skill_name).lower()
        for cand in candidate_skills:
            c_canon = self.get_canonical(cand).lower()
            if s_canon == c_canon:
                return True
            ratio = fuzz.token_sort_ratio(s_canon, c_canon)
            if ratio >= threshold:
                return True
        return False

    def categorize_skills(self, skills: List[str]) -> Dict[str, List[str]]:
        categories: Dict[str, List[str]] = {
            "Languages": [],
            "Backend & Frameworks": [],
            "Frontend": [],
            "Databases & Caching": [],
            "Cloud & DevOps": [],
            "AI / Data Science": [],
            "Architecture & Tools": [],
        }

        lang_set = {"Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "SQL", "HTML5", "CSS3"}
        backend_set = {"Django", "Django REST Framework", "FastAPI", "Flask", "Node.js", "Express.js", "Celery", "REST API", "GraphQL"}
        frontend_set = {"React", "Next.js", "Vue.js", "Angular"}
        db_set = {"PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis"}
        cloud_set = {"Docker", "Kubernetes", "AWS", "Google Cloud Platform", "Microsoft Azure", "CI/CD", "Linux"}
        ai_set = {"Machine Learning", "Deep Learning", "Natural Language Processing", "Scikit-Learn", "TensorFlow", "PyTorch", "Pandas", "NumPy", "spaCy", "NLTK", "Computer Vision"}

        for s in skills:
            canonical = self.get_canonical(s)
            if canonical in lang_set:
                categories["Languages"].append(canonical)
            elif canonical in backend_set:
                categories["Backend & Frameworks"].append(canonical)
            elif canonical in frontend_set:
                categories["Frontend"].append(canonical)
            elif canonical in db_set:
                categories["Databases & Caching"].append(canonical)
            elif canonical in cloud_set:
                categories["Cloud & DevOps"].append(canonical)
            elif canonical in ai_set:
                categories["AI / Data Science"].append(canonical)
            else:
                categories["Architecture & Tools"].append(canonical)

        return {k: v for k, v in categories.items() if v}


# Singleton instance
skill_extractor = SkillExtractor()
