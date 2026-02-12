from sdk.skill_base import SkillBase, SkillMeta
import json
import re

class JsonExtractSkill(SkillBase):
    meta = SkillMeta("json_extract","1.0.0","Data","Medium","Free",True,True)

    input_schema = {
        "type":"object",
        "properties":{"text":{"type":"string","minLength":1}},
        "required":["text"],
        "additionalProperties":False
    }

    output_schema = {
        "type":"object",
        "properties":{"json_objects":{"type":"array","items":{"type":"object"}},"_credits":{"type":"integer"}},
        "required":["json_objects","_credits"],
        "additionalProperties":True
    }

    def execute(self, ctx, inp):
        text = inp["text"]
        # find {...} blocks (simple)
        blocks = re.findall(r"\{.*?\}", text, flags=re.DOTALL)
        out = []
        for b in blocks:
            try:
                out.append(json.loads(b))
            except Exception:
                continue
        return {"json_objects": out}, 0.6, None
