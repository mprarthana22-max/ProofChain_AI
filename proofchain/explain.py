"""Plain-English explanation. The LLM only explains; rules + hash chain decide the verdict.
Only the list of findings is sent to the LLM - never raw data rows."""


def make_llm():
    """Local open-source LLM. Needs `pip install transformers torch` (+ internet once)."""
    try:
        from transformers import pipeline
        gen = pipeline("text2text-generation", model="google/flan-t5-base")
        return lambda p: gen(p, max_new_tokens=120)[0]["generated_text"]
    except Exception as e:
        print("LLM not available, using template explanation:", type(e).__name__)
        return None


def build_prompt(score, verdict, why):
    bullets = "\n".join(f"- {w}" for w in why) or "- no issues found"
    return (f"You are an evidence auditor. Trust score {score}/100, verdict: {verdict}.\n"
            f"Findings:\n{bullets}\n"
            "In 3 sentences, explain this to a non-technical manager and say what to check first.")


def template_explanation(score, verdict, why):
    first = ("compare against the last registered version and ask the file owner who changed it"
             if why else "proceed with normal review")
    concerns = ("Main concerns: " + "; ".join(why) + ". ") if why else "No issues were detected. "
    return f"Verdict: {verdict} (trust {score}/100). {concerns}Recommended first step: {first}."


def explain(score, verdict, why, llm=None):
    if llm is not None:
        try:
            text = llm(build_prompt(score, verdict, why))
            if text and len(text.strip()) > 25:
                return text.strip()
        except Exception:
            pass
    return template_explanation(score, verdict, why)
