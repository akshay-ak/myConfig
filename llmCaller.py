import json
import xml.etree.ElementTree as ET
from fastapi import FastAPI, File, UploadFile, Form
from pydantic import BaseModel
from groq import Groq

# Initialize Groq client
client = Groq(api_key="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")  # Replace with env var or config for security

app = FastAPI(title="myConfig API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Helper functions ---
def parse_context_xml(file_data: bytes):
    def recurse(node):
        children = list(node)
        if children:
            return {child.tag: recurse(child) for child in children}
        else:
            return node.text.strip() if node.text else None

    root = ET.fromstring(file_data)
    return {root.tag: recurse(root)}

def build_prompt(context, ui_rules, user_question):
    return f"""
You are a smart assistant that helps determine the visibility of UI elements based on rules and a user's context.

Context data (from XML):
{json.dumps(context, indent=2)}

UI Elements and their visibility rules:
{json.dumps(ui_rules, indent=2)}

User's Question:
{user_question}

Compare the context data with the visibility rules and explain which conditions are satisfied and which are not. Clearly state whether the element should be visible or not.
"""

def ask_llm(prompt):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": """You evaluate UI element visibility based on context and rules.

                Your role:
                - Answer only based on the question asked.
                - Be accurate, concise, and easy to understand.
                - Use a professional, friendly tone.
                - Ask clarifying questions if needed.

                Key logic rules:
                1. Conditions may be implicit; interpret carefully.
                2. Terms:
                - IA = Is Absent (null or missing XML tag)
                - IP = Is Present (non-empty XML tag)
                - C = Contains (list can be delimited by / or ,)
                    • Example: "TE/CF/MS" contains "TC"? → false
                3. Questions may refer to `presentationText` or `qtag`.
                4. Match logic:
                - Dependency ID = context qtag (convert 30000-3767 → 30000_3767)
                5. Conditions look like:  
                "TP - Filing Eligibility Codes:30000_1866"  
                → Use 30000_1866 to fetch XML value.
                6. Dates are in MM/DD/YYYY format. Compare full date.

                Always keep responses short, relevant, and actionable.
             """},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content


# --- API Models ---
class VisibilityRequest(BaseModel):
    user_question: str
    ui_rules: dict

@app.post("/evaluate-visibility/")
async def evaluate_visibility(user_question: str = Form(...),
                              context_file: UploadFile = File(...),
                              ui_rules_file: UploadFile = File(...)):
    try:
        context_bytes = await context_file.read()
        rules_bytes = await ui_rules_file.read()

        context = parse_context_xml(context_bytes)
        ui_rules = json.loads(rules_bytes.decode('utf-8'))

        prompt = build_prompt(context, ui_rules, user_question)
        answer = ask_llm(prompt)

        return {"response": answer}
    except Exception as e:
        return {"error": str(e)}
