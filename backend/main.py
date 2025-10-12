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

def extract_info_from_doc(doc_bytes, filename=None):
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

    # Extract customer numbers/phone numbers (10-13 digit numbers, or numbers with phone/number in line)
    customer_lines = [line for line in text.splitlines() if re.search(r"(number|phone)", line, re.IGNORECASE)]
    customer_numbers = []
    customer_files = []
    order_amounts = []
    for line in customer_lines:
        # Extract phone numbers (10-13 digits)
        phones = re.findall(r"\b\d{10,13}\b", line)
        if phones:
            for ph in phones:
                customer_numbers.append(ph)
                customer_files.append((ph, filename))

    # Extract order amounts from lines/cells with 'Total bill:' or 'bill:' (case sensitive, with colon)
    bill_lines = [line for line in text.splitlines() if ("Total bill:" in line or "bill:" in line)]
    for line in bill_lines:
        # Try to extract order amount after the colon, possibly with currency
        amt = None
        # Look for 'Total bill: 680', 'bill: 680 tk', etc.
        match = re.search(r"(?:Total bill:|bill:)\s*(\d+[.,]?\d*)", line)
        if match:
            amt = match.group(1)
        # Try to find a customer number in the same line
        phones = re.findall(r"\b\d{10,13}\b", line)
        if amt and phones:
            for ph in phones:
                try:
                    order_amounts.append((ph, float(amt.replace(",", "")), filename))
                except Exception:
                    continue
    return size_counts, customer_numbers, order_amounts, customer_files

@app.post("/analyze")
async def analyze_files(files: list[UploadFile] = File(...)):

    all_sizes = []
    per_file = []
    all_customers = []
    all_order_amounts = []
    all_customer_files = []
    for file in files:
        content = await file.read()
        sizes, customers, order_amounts, customer_files = extract_info_from_doc(content, file.filename)
        all_sizes.extend(sizes)
        all_customers.extend(customers)
        all_order_amounts.extend(order_amounts)
        all_customer_files.extend(customer_files)
        # Per-file top 5
        df_file = pd.Series(sizes, name="size").value_counts().reset_index()
        df_file.columns = ["size", "count"]
        per_file.append({
            "filename": file.filename,
            "top_sizes": df_file.head(5).to_dict(orient="records"),
            "total_orders": len(sizes)
        })

    if not all_sizes:
        return {"top_sizes": [], "total_orders": 0, "per_file": per_file, "top_customers": []}

    df = pd.Series(all_sizes, name="size").value_counts().reset_index()
    df.columns = ["size", "count"]
    top_sizes = df.head(5).to_dict(orient="records")

    # Aggregate customer order counts and amounts
    if all_customers:
        customer_counts = pd.Series(all_customers, name="customer").value_counts().reset_index()
        customer_counts.columns = ["customer", "order_count"]
        # Only keep customers with more than one order (or show all if only one file)
        if len(files) == 1:
            customer_counts = customer_counts[customer_counts["order_count"] >= 1]
        else:
            customer_counts = customer_counts[customer_counts["order_count"] > 1]
        # Aggregate order amounts by customer
        if all_order_amounts:
            df_amt = pd.DataFrame(all_order_amounts, columns=["customer", "amount", "filename"])
            amt_sum = df_amt.groupby("customer")["amount"].sum().reset_index()
            customer_counts = customer_counts.merge(amt_sum, on="customer", how="left")
        else:
            customer_counts["amount"] = 0
        # Aggregate filenames for each customer
        if all_customer_files:
            df_files = pd.DataFrame(all_customer_files, columns=["customer", "filename"])
            file_map = df_files.groupby("customer")["filename"].apply(lambda x: ", ".join(sorted(set(x)))).reset_index()
            customer_counts = customer_counts.merge(file_map, on="customer", how="left")
        else:
            customer_counts["filename"] = ""
        top_customers = customer_counts.head(20).to_dict(orient="records")
    else:
        top_customers = []

    return {"top_sizes": top_sizes, "total_orders": len(all_sizes), "per_file": per_file, "top_customers": top_customers}
