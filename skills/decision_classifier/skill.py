from sdk.skill_base import SkillBase, SkillMeta

class DecisionClassifierSkill(SkillBase):
    meta = SkillMeta("decision_classifier","1.0.0","Decision","Medium","Free",True,True)

    input_schema = {
        "type":"object",
        "properties":{"text":{"type":"string","minLength":1}},
        "required":["text"],
        "additionalProperties":False
    }

    output_schema = {
        "type":"object",
        "properties":{"decision":{"type":"string"},"reason":{"type":"string"},"_credits":{"type":"integer"}},
        "required":["decision","reason","_credits"],
        "additionalProperties":True
    }

    def execute(self, ctx, inp):
        t = inp["text"].lower()
        if "api key" in t or "password" in t or "secret" in t:
            return {"decision":"BLOCK","reason":"Contains sensitive request"}, 0.9, {"rule":"sensitive_terms"}
        if "ignore policy" in t or "jailbreak" in t:
            return {"decision":"BLOCK","reason":"Prompt injection attempt"}, 0.9, {"rule":"prompt_injection"}
        return {"decision":"ALLOW","reason":"No risky patterns found"}, 0.7, {"rule":"default_allow"}
