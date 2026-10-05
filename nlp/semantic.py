from typing import Dict, List, Set, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
SEMANTIC_THRESHOLD = 0.45

MODEL = SentenceTransformer(MODEL_NAME)

SKILL_DESCRIPTIONS = {
    "nlp": "natural language processing and computational linguistics",
    "ml": "machine learning and predictive statistical modeling",
    "ai": "artificial intelligence and intelligent systems",
    "deep learning": "deep learning neural networks and representation learning",
    "llm": "large language models generative ai and transformers",
    "rag": "retrieval augmented generation knowledge retrieval",
    "cnn": "convolutional neural networks image classification computer vision",
    "ann": "artificial neural networks deep learning",
    "rnn": "recurrent neural networks sequence modeling",
    "lstm": "long short-term memory recurrent networks",
    "transformers": "transformer attention models bert and gpt architecture",
    "cpp": "c++ programming language systems development",
    "c": "c programming language low level systems",
    "oop": "object oriented programming design patterns and architecture",
    "data structures and algorithms": "data structures and algorithms problem solving complexity analysis",
    "computer vision": "computer vision image processing visual recognition",
    "aws": "amazon web services cloud computing infrastructure",
    "gcp": "google cloud platform cloud infrastructure",
    "azure": "microsoft azure cloud computing infrastructure",
    "kubernetes": "kubernetes container orchestration and cluster management",
    "docker": "docker containerization virtualization microservices",
    "devops": "devops continuous integration deployment automation",
    "seo": "search engine optimization search ranking content visibility",
    "crm": "customer relationship management client software",
    "big data": "big data distributed systems and large scale data processing",
    "data engineering": "data engineering pipelines etl and warehouse architectures",
}


def describe_skill(skill: str) -> str:
    cleaned = skill.strip().lower()
    return SKILL_DESCRIPTIONS.get(cleaned, cleaned)


def semantic_skill_matching(
    job_skills: List[str],
    candidate_skills: List[str],
    exact_job_skills: Set[str] | None = None,
    threshold: float = SEMANTIC_THRESHOLD,
) -> Tuple[float, List[Tuple[str, str, float]]]:
    """Match remaining job skills to candidate skills using embeddings.

    Exact matches are excluded so the same requirement cannot receive both
    exact and semantic credit. Candidate skills are matched greedily once to
    avoid reusing one candidate skill for several semantic requirements.
    """
    exact_job_skills = exact_job_skills or set()

    job_skills = [s.strip().lower() for s in job_skills if s.strip()]
    candidate_skills = [s.strip().lower() for s in candidate_skills if s.strip()]

    # Do not reuse an exact candidate skill as semantic evidence for another requirement.
    candidate_skills = [s for s in candidate_skills if s not in exact_job_skills]
    remaining_jobs = [s for s in job_skills if s not in exact_job_skills]
    if not remaining_jobs or not candidate_skills:
        return 0.0, []

    # Contextual expansion allows acronyms (e.g. 'nlp', 'llm') to produce rich dense vectors
    expanded_jobs = [describe_skill(s) for s in remaining_jobs]
    expanded_candidates = [describe_skill(s) for s in candidate_skills]

    embeddings = MODEL.encode(
        expanded_jobs + expanded_candidates,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype(np.float32)

    job_embeddings = embeddings[: len(remaining_jobs)]
    candidate_embeddings = embeddings[len(remaining_jobs):]
    matrix = job_embeddings @ candidate_embeddings.T

    pairs = []
    for i, job_skill in enumerate(remaining_jobs):
        for j, candidate_skill in enumerate(candidate_skills):
            pairs.append((float(matrix[i, j]), i, j, job_skill, candidate_skill))

    # Greedy one-to-one matching: strongest semantic pairs are selected first.
    pairs.sort(reverse=True, key=lambda item: item[0])
    used_jobs = set()
    used_candidates = set()
    matches: List[Tuple[str, str, float]] = []
    score_sum = 0.0

    for similarity, job_index, candidate_index, job_skill, candidate_skill in pairs:
        if similarity < threshold:
            break
        if job_index in used_jobs or candidate_index in used_candidates:
            continue

        used_jobs.add(job_index)
        used_candidates.add(candidate_index)

        normalized_credit = float(
            np.clip((similarity - threshold) / (1.0 - threshold), 0.0, 1.0)
        )
        score_sum += normalized_credit
        matches.append((job_skill, candidate_skill, similarity))

    semantic_score = score_sum / len(job_skills)
    matches.sort(key=lambda item: item[0])

    return semantic_score, matches
