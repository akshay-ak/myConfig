import json
import xml.etree.ElementTree as ET
import os
from groq import Groq

client = Groq(
    api_key="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"
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role":"user",
            "content": "Explain the importance of low latency LLMs. Responsd in just 1 line. Keep it simple"
        }
    ],
    model="llama-3.3-70b-versatile"
)


# --- Load XML context data ---
def load_context_xml(file_path):
    def recurse(node):
        children = list(node)
        if children:
            return {child.tag: recurse(child) for child in children}
        else:
            return node.text.strip() if node.text else None
    tree = ET.parse(file_path)
    return {tree.getroot().tag: recurse(tree.getroot())}

# --- Load UI element rules ---
def load_ui_rules(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# --- Build prompt for LLM ---
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

# --- Query OpenAI LLM ---
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

# --- Main chat interface ---
def chatbot(context_file, ui_rules_file):
    context = load_context_xml(context_file)
    ui_rules = load_ui_rules(ui_rules_file)
    print("Type your question (or 'exit' to quit):")
    while True:
        question = input("You: ")
        if question.lower() in ["exit", "quit"]:
            break
        prompt = build_prompt(context, ui_rules, question)
        answer = ask_llm(prompt)
        print("\nAssistant:", answer, "\n")

# --- Run chatbot ---
if __name__ == "__main__":
    chatbot("cdmXML.xml", "dependencies.json")
