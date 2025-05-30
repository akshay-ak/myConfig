from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import xml.etree.ElementTree as ET
import json
from groq import Groq

# Initialize Groq client
client = Groq(api_key="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")

app = FastAPI(title="myConfig API")

# Optional: CORS middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request Model ---
class UserQuestion(BaseModel):
    user_question: str

# --- Load files from local directory ---
def load_context_xml(file_path):
    def recurse(node):
        children = list(node)
        if children:
            return {child.tag: recurse(child) for child in children}
        else:
            return node.text.strip() if node.text else None

    tree = ET.parse(file_path)
    return {tree.getroot().tag: recurse(tree.getroot())}

def load_ui_rules(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

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
             You evaluate UI element visibility based on context and rules.

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

# --- API Endpoint ---
@app.post("/evaluate-visibility/")
def evaluate_visibility(payload: UserQuestion):
    try:
        context = load_context_xml("cdmXML.xml")
        ui_rules = load_ui_rules("dependencies.json")
        prompt = build_prompt(context, ui_rules, payload.user_question)
        answer = ask_llm(prompt)
        return {"response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
def health():
    return {"status": "ok"}
