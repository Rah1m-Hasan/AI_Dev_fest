"""A bounded explanation layer. It only sees computed evidence, never database access."""
import httpx
from app.core.config import get_settings
SYSTEM_PROMPT = """You are Upay AI Financial Coach, an informational money-management assistant. Use only the provided structured context. Never invent transactions, balances, predictions, or guarantees. Do not approve lending or shame users. Separate historical facts from forecasts. Give concise, practical, optional actions. Use Bangladeshi Taka. Important actions remain controlled by the user."""
def fallback(kind:str, evidence:dict, language="en"):
    if kind=="run_out":
        change=evidence.get("expense_change_percent"); cat=evidence.get("largest_change",{}).get("category")
        return f"Your calculated spending this month is ৳{evidence['total_expense']:,.0f}." + (f" That is {abs(change):.0f}% {'higher' if change>=0 else 'lower'} than the previous period." if change is not None else "") + (f" {cat} changed the most." if cat else "") + f" The highest-spending week was week {evidence.get('critical_week')}. Consider a weekly target and reviewing recurring payments of ৳{evidence['recurring_expenses']:,.0f}."
    return "AI explanation is temporarily unavailable. The calculated facts shown here remain available."
async def explain(kind:str,evidence:dict, question:str="",language="en"):
    s=get_settings()
    if not s.groq_api_key: return {"text":fallback(kind,evidence,language),"provider":"deterministic_fallback"}
    payload={"model":s.groq_model,"temperature":0.2,"max_tokens":280,"messages":[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":f"Question: {question[:500]}\nStructured context (authoritative): {evidence}\nLanguage: {language}"}]}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r=await client.post("https://api.groq.com/openai/v1/chat/completions",headers={"Authorization":f"Bearer {s.groq_api_key}"},json=payload); r.raise_for_status()
            return {"text":r.json()["choices"][0]["message"]["content"],"provider":"groq_grounded"}
    except Exception: return {"text":fallback(kind,evidence,language),"provider":"deterministic_fallback"}
