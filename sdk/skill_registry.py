from __future__ import annotations

# Import skills that exist in your repo
from skills.summarization.skill import SummarizeSkill
from skills.translation.skill import TranslateSkill

# If you already created these skills in your earlier steps, keep them.
# If any import fails, comment that line and remove from SKILL_IMPLS.
try:
    from skills.clean_text.skill import CleanTextSkill
except Exception:
    CleanTextSkill = None

try:
    from skills.pii_redactor.skill import PiiRedactorSkill
except Exception:
    PiiRedactorSkill = None

SKILL_IMPLS = {
    "summarize": SummarizeSkill,
    "translate": TranslateSkill,
}

if CleanTextSkill:
    SKILL_IMPLS["clean_text"] = CleanTextSkill

if PiiRedactorSkill:
    SKILL_IMPLS["pii_redactor"] = PiiRedactorSkill
