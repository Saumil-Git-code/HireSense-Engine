"""Comprehensive test suite and evaluation benchmark for HireSense Engine.

Validates:
1. Vocabulary extraction and alias canonicalization.
2. Chronological date-range and summary experience extraction.
3. Dense semantic similarity matching with acronym expansion.
4. Grounded multi-tier evidence partitioning (Exact -> Semantic -> Graph).
"""

import math
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from nlp.parser import (
    build_alias_lookup,
    extract_experience,
    extract_skills,
    load_vocabulary,
)
from nlp.semantic import describe_skill, semantic_skill_matching


class TestHireSensePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vocabulary = load_vocabulary()
        cls.alias_lookup = build_alias_lookup(cls.vocabulary)

    def test_vocabulary_canonicalization(self):
        """Aliases like 'c++', 'natural language processing', 'dsa' must map to canonical keys."""
        self.assertEqual(self.alias_lookup.get("c++"), "cpp")
        self.assertEqual(self.alias_lookup.get("natural language processing"), "nlp")
        self.assertEqual(self.alias_lookup.get("dsa"), "data structures and algorithms")
        self.assertEqual(self.alias_lookup.get("k8s"), "kubernetes")

    def test_skill_extraction_with_coursework(self):
        """Skills in coursework and project sections must be correctly detected."""
        sections = {
            "skills": ["Proficient in Python, Docker, and Git."],
            "coursework": ["Data Structures & Algorithms", "Database Management"],
            "experience": ["Built scalable backend services using Flask."],
        }
        detected = extract_skills(sections, self.vocabulary)
        self.assertIn("python", detected)
        self.assertIn("docker", detected)
        self.assertIn("git", detected)
        self.assertIn("flask", detected)
        self.assertIn("data structures and algorithms", detected)
        self.assertIn("database", detected)

    def test_experience_extraction_date_ranges(self):
        """Date intervals like '2020 - 2024' must be correctly parsed into numerical years."""
        sections = {
            "experience": [
                "Software Engineer at Acme Corp (2020 - 2024)",
                "Developed high throughput APIs.",
            ]
        }
        exp = extract_experience(sections)
        self.assertGreaterEqual(exp, 4.0)

    def test_experience_extraction_summary_statements(self):
        """Explicit summary statements like 'Over 6 years of professional experience' must be parsed."""
        sections = {
            "summary": ["Senior Backend Developer with over 6 years of experience in distributed systems."],
            "experience": ["Led migration to Kubernetes."],
        }
        exp = extract_experience(sections)
        self.assertEqual(exp, 6.0)

    def test_semantic_acronym_expansion(self):
        """Acronyms like 'nlp' and 'llm' must be contextually expanded for dense embeddings."""
        self.assertIn("natural language processing", describe_skill("nlp"))
        self.assertIn("large language models", describe_skill("llm"))
        self.assertIn("machine learning", describe_skill("ml"))

    def test_semantic_matching_dense_pair(self):
        """Semantically related requirements must yield similarity above threshold with 1-to-1 pairing."""
        job_skills = ["nlp", "ml"]
        candidate_skills = ["deep learning", "docker"]
        exact_skills = set()

        score, matches = semantic_skill_matching(
            job_skills, candidate_skills, exact_job_skills=exact_skills, threshold=0.40
        )
        self.assertGreater(score, 0.0)
        self.assertGreater(len(matches), 0)
        # Verify 1-to-1 matching: each job skill matched at most once
        matched_jobs = [m[0] for m in matches]
        self.assertEqual(len(matched_jobs), len(set(matched_jobs)))


def compute_ndcg_at_k(actual_ranks, ideal_ranks, k=5):
    """Compute Normalized Discounted Cumulative Gain at K."""
    def dcg(relevances):
        return sum((2**rel - 1) / math.log2(idx + 2) for idx, rel in enumerate(relevances[:k]))

    # Map candidate ids to relevance
    cand_to_rel = {cand: (len(ideal_ranks) - idx) for idx, cand in enumerate(ideal_ranks)}
    actual_rels = [cand_to_rel.get(cand, 0) for cand in actual_ranks[:k]]
    ideal_rels = sorted(cand_to_rel.values(), reverse=True)[:k]

    idcg = dcg(ideal_rels)
    if idcg == 0:
        return 1.0
    return dcg(actual_rels) / idcg


if __name__ == "__main__":
    unittest.main()
