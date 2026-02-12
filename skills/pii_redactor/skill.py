from sdk.skill_base import SkillBase, SkillMeta
import re

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\b(\+?\d[\d\s\-]{7,}\d)\b")

class PiiRedactorSkill(SkillBase):
    meta = SkillMeta("pii_redactor","1.0.0","Governance","Medium","Free",True,True)

    input_schema = {
        "type":"object",
        "properties":{"text":{"type":"string","minLength":1}},
        "required":["text"],
        "additionalProperties":False
    }

    output_schema = {
        "type":"object",
        "properties":{"redacted":{"type":"string"},"_credits":{"type":"integer"}},
        "required":["redacted","_credits"],
        "additionalProperties":True
    }

    def execute(self, ctx, inp):
        text = inp["text"]
        text = EMAIL.sub("[REDACTED_EMAIL]", text)
        text = PHONE.sub("[REDACTED_PHONE]", text)
        return {"redacted": text}, 0.8, None
