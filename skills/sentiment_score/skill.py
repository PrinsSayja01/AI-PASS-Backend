from sdk.skill_base import SkillBase, SkillMeta

POS = set(["good","great","awesome","nice","love","happy","excellent","amazing"])
NEG = set(["bad","worst","hate","sad","terrible","awful","angry","poor"])

class SentimentScoreSkill(SkillBase):
    meta = SkillMeta("sentiment_score","1.0.0","Reasoning","Low","Free",False,True)

    input_schema = {
        "type":"object",
        "properties":{"text":{"type":"string","minLength":1}},
        "required":["text"],
        "additionalProperties":False
    }

    output_schema = {
        "type":"object",
        "properties":{"score":{"type":"number"},"label":{"type":"string"},"_credits":{"type":"integer"}},
        "required":["score","label","_credits"],
        "additionalProperties":True
    }

    def execute(self, ctx, inp):
        words = [w.strip(".,!?").lower() for w in inp["text"].split()]
        pos = sum(1 for w in words if w in POS)
        neg = sum(1 for w in words if w in NEG)
        total = max(1, pos + neg)
        score = (pos - neg) / total
        label = "positive" if score > 0.2 else "negative" if score < -0.2 else "neutral"
        return {"score": float(score), "label": label}, 0.7, None
