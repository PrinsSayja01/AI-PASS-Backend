from sdk.skill_base import SkillBase, SkillMeta
import re

class CleanTextSkill(SkillBase):
    meta = SkillMeta("clean_text","1.0.0","Data","Low","Free",False,True)

    input_schema = {
        "type":"object",
        "properties":{"text":{"type":"string","minLength":1}},
        "required":["text"],
        "additionalProperties":False
    }

    output_schema = {
        "type":"object",
        "properties":{"cleaned":{"type":"string"},"_credits":{"type":"integer"}},
        "required":["cleaned","_credits"],
        "additionalProperties":True
    }

    def execute(self, ctx, inp):
        t = inp["text"]
        t = re.sub(r"\s+", " ", t).strip()
        return {"cleaned": t}, 0.95, None
