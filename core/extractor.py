"""
Claim Extraction - Mock version.
Returns mock claims without using AI.
"""

def extract_claims_from_paper(paper_text: str) -> list:
    """Extract mock claims from paper text."""
    return [
        {
            "id": "claim_1",
            "test_type": "t_test_independent",
            "claimed_p_value": 0.03,
            "claimed_effect_size": 0.45,
            "params": {
                "group_col": "treatment_group",
                "value_col": "cognitive_score"
            },
            "claim_statement": "Exercise significantly improved cognitive scores versus control",
            "source": "mock_extracted",
            "extraction_confidence": "high"
        }
    ]
