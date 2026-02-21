from openai import OpenAI
from pydantic import BaseModel
from fastapi import FastAPI


from fastapi.responses import FileResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


app = FastAPI()


client = OpenAI(
 base_url="https://api.featherless.ai/v1",
 api_key="rc_948fc6d4e6b6e13cf914448bae5045c3be2a2cd80d499cb0ac8e3e2cbd8cd306",
)


# ✅ Request Body
class ConversationRequest(BaseModel):
   conversation: str


def create_emr_pdf(emr_text, filename="emr_report.pdf"):


   doc = SimpleDocTemplate(filename, pagesize=letter)
   styles = getSampleStyleSheet()


   title_style = ParagraphStyle('Title', fontSize=18, spaceAfter=20)
   section_style = ParagraphStyle('Section', fontSize=12, spaceAfter=8)


   elements = []


   elements.append(Paragraph("Electronic Medical Record", title_style))
   elements.append(Spacer(1, 12))


   for line in emr_text.split("\n"):
       if line.strip():
           elements.append(Paragraph(line, section_style))


   doc.build(elements)


   return filename


# ✅ Endpoint 1 — FULL EMR DOCUMENT
@app.post("/generate-emr")
def generate_emr(request: ConversationRequest):


   response = client.chat.completions.create(
       model="meta-llama/Llama-3.1-8B-Instruct",
       messages=[
           {
               "role": "system",
               "content": "You are a clinical documentation assistant generating professional EMR notes."
           },
           {
               "role": "user",
               "content": f"""
Generate a complete Electronic Medical Record (EMR) summary.


Conversation:
{request.conversation}


Include ALL relevant sections:


- Patient Information (if available)
- Chief Complaint
- History of Present Illness (HPI)
- Symptoms
- Duration
- Medications Mentioned
- Allergies (if mentioned)
- Assessment
- Plan
- Follow-up Recommendations


Use professional clinical language.
"""
           }
       ],
   )


   emr_text = response.model_dump()['choices'][0]['message']['content']


   pdf_path = create_emr_pdf(emr_text)


   return FileResponse(
       pdf_path,
       media_type="application/pdf",
       filename="EMR_Report.pdf"
   )




# ✅ Endpoint 2 — STRUCTURED JSON (VERY IMPORTANT)
@app.post("/generate-json")
def generate_json(request: ConversationRequest):


   response = client.chat.completions.create(
       model="meta-llama/Llama-3.1-8B-Instruct",
       messages=[
           {
               "role": "system",
               "content": "You are a medical data extraction assistant."
           },
           {
               "role": "user",
               "content": f"""
Convert this doctor-patient conversation into VALID JSON.


Conversation:
{request.conversation}


Return ONLY valid JSON.


Fields:


- chief_complaint
- symptoms
- duration
- medications
- allergies
- assessment
- plan
- follow_up


Do not include explanations.
Do not include extra text.
"""
           }
       ],
   )


   return {
       "structured_data": response.model_dump()['choices'][0]['message']['content']
   }

