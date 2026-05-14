from app.schemas.ai import AIDecision


class LeadScoringService:
    def score_delta(self, decision: AIDecision, repeat_engagements: int = 0) -> int:
        score = decision.lead_score_delta
        score += int(decision.purchase_intent * 35)
        score += min(repeat_engagements * 5, 20)

        if decision.intent in {"purchase_intent", "price_question"}:
            score += 15
        if decision.urgency == "high":
            score += 10
        if decision.safety_flags:
            score -= 10
        return max(-20, min(score, 100))

