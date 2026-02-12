from sdk.skill_base import SkillBase, SkillMeta

class LanguageDetectSkill(SkillBase):
    meta = SkillMeta("language_detect","1.0.0","Data","Low","Free",False,True)

    input_schema = {
        "type":"object",
        "properties":{"text":{"type":"string","minLength":1}},
        "required":["text"],
        "additionalProperties":False
    }

    output_schema = {
        "type":"object",
        "properties":{"lang":{"type":"string"},"confidence":{"type":"number"},"_credits":{"type":"integer"}},
        "required":["lang","confidence","_credits"],
        "additionalProperties":True
    }

    def execute(self, ctx, inp):
        text = inp["text"]
        # very basic: if text has many non-ascii -> assume "de" else "en"
        non_ascii = sum(1 for c in text if ord(c) > 127)
        conf = min(0.9, 0.5 + non_ascii / max(1, len(text)))
        lang = "de" if non_ascii > 0 else "en"
        return {"lang": lang, "confidence": float(conf)}, 0.6, None
