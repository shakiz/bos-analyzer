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
    # Combine all text from paragraphs
    text = "\n".join(p.text for p in document.paragraphs)
    # Also add all table cell text (if any)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text
    # Find all lines with 'size' (case-insensitive)
    size_lines = [line for line in text.splitlines() if re.search(r"size", line, re.IGNORECASE)]
    size_counts = []
    for line in size_lines:
        # Extract numbers from the line
        nums = re.findall(r"\d{2,3}", line)
        size_counts.extend(nums)
    return size_counts

@app.post("/analyze")
async def analyze_files(files: list[UploadFile] = File(...)):
    all_sizes = []
    per_file = []
    for file in files:
        content = await file.read()
        sizes = extract_size_from_doc(content)
        all_sizes.extend(sizes)
        # Per-file top 5
        df_file = pd.Series(sizes, name="size").value_counts().reset_index()
        df_file.columns = ["size", "count"]
        per_file.append({
            "filename": file.filename,
            "top_sizes": df_file.head(5).to_dict(orient="records"),
            "total_orders": len(sizes)
        })

    if not all_sizes:
        return {"top_sizes": [], "total_orders": 0, "per_file": per_file}

    df = pd.Series(all_sizes, name="size").value_counts().reset_index()
    df.columns = ["size", "count"]
    top_sizes = df.head(5).to_dict(orient="records")
    return {"top_sizes": top_sizes, "total_orders": len(all_sizes), "per_file": per_file}
