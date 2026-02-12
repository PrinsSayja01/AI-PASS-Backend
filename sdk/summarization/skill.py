from sdk.skill_base import SkillBase, SkillMeta

class SummarizeSkill(SkillBase):
    meta = SkillMeta(
        skill_id="summarize",
        version="1.0.0",
        category="Reasoning",
        risk_level="Low",
        plan_tier="Free",
        explainability=False,
        deterministic=False
    )

    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "minLength": 1},
            "max_words": {"type": "integer", "minimum": 20, "maximum": 400}
        },
        "required": ["text"],
        "additionalProperties": False
    }

    output_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "_credits": {"type": "integer"}
        },
        "required": ["summary", "_credits"],
        "additionalProperties": True
    }

    def execute(self, ctx, inp):
        text = inp["text"]
        max_words = inp.get("max_words", 120)
        words = text.split()
        summary = " ".join(words[:max_words])
        return {"summary": summary}, 0.65, None
