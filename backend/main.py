from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
import pandas as pd
import re
from io import BytesIO

app = FastAPI()

# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_size_from_doc(doc_bytes):
    document = Document(BytesIO(doc_bytes))
    text = "\n".join(p.text for p in document.paragraphs)
    sizes = re.findall(r"Size[:\-\s]*([0-9,\s]+)", text, re.IGNORECASE)
    size_counts = []
    for group in sizes:
        nums = re.findall(r"\d{2}", group)
        size_counts.extend(nums)
    return size_counts

@app.post("/analyze")
async def analyze_files(files: list[UploadFile] = File(...)):
    all_sizes = []
    for file in files:
        content = await file.read()
        sizes = extract_size_from_doc(content)
        all_sizes.extend(sizes)

    if not all_sizes:
        return {"top_sizes": [], "total_orders": 0}

    df = pd.Series(all_sizes, name="size").value_counts().reset_index()
    df.columns = ["size", "count"]

    top_sizes = df.head(5).to_dict(orient="records")
    return {"top_sizes": top_sizes, "total_orders": len(all_sizes)}
