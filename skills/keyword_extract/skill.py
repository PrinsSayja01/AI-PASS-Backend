from sdk.skill_base import SkillBase, SkillMeta
import re
from collections import Counter

STOP = set(["the","a","an","and","or","is","are","to","of","in","on","for","with","this","that","it","as","at","by"])

class KeywordExtractSkill(SkillBase):
    meta = SkillMeta("keyword_extract","1.0.0","Reasoning","Low","Free",False,True)

    input_schema = {
        "type":"object",
        "properties":{"text":{"type":"string","minLength":1},"top_k":{"type":"integer","minimum":3,"maximum":30}},
        "required":["text"],
        "additionalProperties":False
    }

    output_schema = {
        "type":"object",
        "properties":{"keywords":{"type":"array","items":{"type":"string"}},"_credits":{"type":"integer"}},
        "required":["keywords","_credits"],
        "additionalProperties":True
    }

    def execute(self, ctx, inp):
        text = inp["text"].lower()
        top_k = inp.get("top_k", 10)
        words = re.findall(r"[a-zA-Z0-9']{2,}", text)
        words = [w for w in words if w not in STOP]
        common = [w for w,_ in Counter(words).most_common(top_k)]
        return {"keywords": common}, 0.7, None
