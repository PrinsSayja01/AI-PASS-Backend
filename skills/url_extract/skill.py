from sdk.skill_base import SkillBase, SkillMeta
import re

URL = re.compile(r"(https?://[^\s'\"<>]+)", re.IGNORECASE)

class UrlExtractSkill(SkillBase):
    meta = SkillMeta("url_extract","1.0.0","Data","Low","Free",False,True)

    input_schema = {
        "type":"object",
        "properties":{"text":{"type":"string","minLength":1}},
        "required":["text"],
        "additionalProperties":False
    }

    output_schema = {
        "type":"object",
        "properties":{"urls":{"type":"array","items":{"type":"string"}},"_credits":{"type":"integer"}},
        "required":["urls","_credits"],
        "additionalProperties":True
    }

    def execute(self, ctx, inp):
        urls = URL.findall(inp["text"])
        return {"urls": urls}, 0.85, None
