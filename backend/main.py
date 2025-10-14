from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from docx import Document
import pandas as pd
import re
from io import BytesIO
from typing import List, Tuple

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------
# Helpers
# -------------------
def clean_text(s: str) -> str:
    s = s.replace("\xa0", " ").replace("\u200b", "").strip()
    # keep line breaks for block splitting, normalize multiple spaces
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\r\n?", "\n", s)
    return s

def normalize_phone_candidates(text: str) -> List[str]:
    """
    Find potential phone strings (allow spaces/dashes) and return normalized digits-only phones of length 10-13.
    """
    # Find sequences containing digits, spaces, dashes of reasonable length
    candidates = re.findall(r"(?:\+?\d[\d\s\-\(\)]{7,}\d)", text)
    phones = []
    for c in candidates:
        digits = re.sub(r"\D", "", c)
        if 9 < len(digits) <= 13:
            phones.append(digits)
    # also fallback to contiguous digits
    more = re.findall(r"\b\d{10,13}\b", text)
    for m in more:
        if m not in phones:
            phones.append(m)
    return phones

def eval_bill_expression(expr: str) -> float:
    """
    Given a substring likely containing numbers and + - * / and maybe '=', return numeric total.
    Strategy:
     - If '=' present, take RHS (after last '='), extract last numeric token.
     - Else if '+' or other operators present, try to safely evaluate cleaned expression.
     - Otherwise, return last numeric token found.
    """
    if not expr or not isinstance(expr, str):
        raise ValueError("empty expr")
    # Remove currency words and stray letters
    expr_clean = expr.replace("taka", "").replace("tk", "").replace("Taka", "").replace(",", " ").strip()
    # If '=' present: take RHS
    if "=" in expr_clean:
        rhs = expr_clean.split("=")[-1]
        nums = re.findall(r"\d+[.,]?\d*", rhs)
        if nums:
            return float(nums[-1].replace(",", ""))
    # If contains arithmetic operators, try evaluate
    if re.search(r"[+\-*/]", expr_clean):
        # Keep only digits and operators and dots
        safe = re.sub(r"[^\d+\-*/.() ]", "", expr_clean)
        # As a last safety, ensure safe matches only allowed chars
        if re.fullmatch(r"[0-9+\-*/.\s()]+", safe):
            try:
                val = eval(safe, {"__builtins__": None}, {})
                return float(val)
            except Exception:
                pass
    # Fallback: last numeric token
    nums = re.findall(r"\d+[.,]?\d*", expr_clean)
    if nums:
        return float(nums[-1].replace(",", ""))
    raise ValueError("Could not parse amount from: " + expr)

def find_bill_lines(text: str) -> List[Tuple[int, str]]:
    """Return list of (line_index, line_text) that look like bill lines."""
    lines = text.splitlines()
    results = []
    for i, line in enumerate(lines):
        if re.search(r"(?:total\s*bill|bill)[:\-]?", line, re.IGNORECASE):
            results.append((i, line.strip()))
    return results

# -------------------
# Main extractor (keeps your structure but more robust)
# -------------------
def extract_info_from_doc(doc_bytes, filename=None, debug=False):
    document = Document(BytesIO(doc_bytes))
    paragraphs = [p.text for p in document.paragraphs if p.text and p.text.strip() != ""]
    # collect table cell text too
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text and cell.text.strip() != "":
                    paragraphs.append(cell.text)

    # Join with single newline between paragraphs so we can split into blocks reliably
    raw_text = "\n".join(paragraphs)
    raw_text = clean_text(raw_text)

    # Build blocks. Prefer splitting on occurrences of "Name" or on two+ newlines.
    # We preserve order.
    # First attempt: split on "Name" headings (keep the "Name" token with block using lookahead)
    blocks = re.split(r"(?i)(?=^Name[:\-\s])", raw_text, flags=re.MULTILINE)
    if len(blocks) <= 1:
        # fallback: split on double-newline blocks
        blocks = [b.strip() for b in re.split(r"\n{2,}", raw_text) if b.strip()]

    # For debugging, keep raw blocks
    debug_blocks = blocks.copy()

    size_counts = []
    customer_numbers = []
    customer_files = []
    order_amounts = []  # tuples (customer, amount, filename)

    # Precompute all phone candidates in document
    doc_phones = normalize_phone_candidates(raw_text)

    # Precompute all bill lines (index in lines + text)
    bill_lines = find_bill_lines(raw_text)
    # Map line index -> expression string (extracted)
    line_expr_map = {}
    for idx, line in bill_lines:
        m = re.search(r"(?:total\s*bill|bill)[:\-]?\s*(.*)", line, re.IGNORECASE)
        if m:
            line_expr_map[idx] = m.group(1).strip()

    # Process each block using your original logic but with better phone normalization and local bill association
    for block_idx, block in enumerate(blocks):
        b = block.strip()
        if not b:
            continue

        # Extract sizes (original approach)
        # but limit to lines that contain 'size' to avoid catching numbers from addresses
        block_size_lines = [line for line in b.splitlines() if re.search(r"\bsize\b", line, re.IGNORECASE)]
        for line in block_size_lines:
            nums = re.findall(r"\d{2,3}", line)
            size_counts.extend(nums)

        # Extract customer numbers (original logic but normalized)
        block_customer_lines = [line for line in b.splitlines() if re.search(r"(number|phone)", line, re.IGNORECASE)]
        for line in block_customer_lines:
            phones = normalize_phone_candidates(line)
            for ph in phones:
                customer_numbers.append(ph)
                customer_files.append((ph, filename))

        # If no phone in explicit "Number/Phone" lines, also search entire block
        if not block_customer_lines:
            phones = normalize_phone_candidates(b)
            for ph in phones:
                if ph not in customer_numbers:
                    customer_numbers.append(ph)
                    customer_files.append((ph, filename))

        # --- Bill extraction inside block ---
        # First, look for explicit "bill" inside the block lines
        block_lines = b.splitlines()
        found_amt_for_block = False
        for i, line in enumerate(block_lines):
            if re.search(r"(?:total\s*bill|bill)[:\-]?", line, re.IGNORECASE):
                # extract expression after the label
                m = re.search(r"(?:total\s*bill|bill)[:\-]?\s*(.*)", line, re.IGNORECASE)
                expr = m.group(1).strip() if m else ""
                # Evaluate robustly
                try:
                    amt = eval_bill_expression(expr)
                    # attach amt to phones found in this block (prefer those)
                    phones_here = normalize_phone_candidates("\n".join(block_lines))
                    if phones_here:
                        for ph in phones_here:
                            order_amounts.append((ph, amt, filename))
                    else:
                        # fallback to doc phones or unknown
                        if doc_phones:
                            for ph in doc_phones:
                                order_amounts.append((ph, amt, filename))
                        else:
                            order_amounts.append(("unknown", amt, filename))
                    found_amt_for_block = True
                except Exception:
                    # ignore parse failure here, we'll try neighbor lines later
                    pass

        # If no explicit bill line in this block, try nearby lines in the document (lookahead/back)
        if not found_amt_for_block:
            # Try to find a bill line within the next 3 lines in the global document (using bill_lines map)
            # Map block to approximate global line indices
            # Build global lines list once
            pass

    # --- Fallback: if order_amounts is empty but bill lines exist, attach those to nearest phone(s) globally ---
    if not order_amounts and line_expr_map:
        for idx, expr in line_expr_map.items():
            try:
                amt = eval_bill_expression(expr)
            except Exception:
                continue
            # attach to doc phones if any, else unknown
            if doc_phones:
                for ph in doc_phones:
                    order_amounts.append((ph, amt, filename))
            else:
                order_amounts.append(("unknown", amt, filename))

    # For debug: include what bill lines and phones we found
    debug_info = {
        "raw_text_snippet": raw_text[:2000],
        "doc_phones": doc_phones,
        "bill_lines_count": len(bill_lines),
        "bill_line_examples": bill_lines[:5],
        "blocks_sample": debug_blocks[:6],
        "order_amounts_found": order_amounts[:20],
    }

    return size_counts, customer_numbers, order_amounts, customer_files, debug_info

# -------------------
# API Endpoint
# -------------------
@app.post("/analyze")
async def analyze_files(files: List[UploadFile] = File(...)):
    all_sizes = []
    per_file = []
    all_customers = []
    all_customer_files = []
    all_order_amounts = []
    debug_collection = []

    for file in files:
        content = await file.read()
        sizes, customers, order_amounts, customer_files, debug_info = extract_info_from_doc(content, file.filename, debug=True)
        all_sizes.extend(sizes)
        all_customers.extend(customers)
        all_customer_files.extend(customer_files)
        all_order_amounts.extend(order_amounts)
        per_df = pd.Series(sizes, name="size").value_counts().reset_index()
        per_df.columns = ["size", "count"]
        per_file.append({
            "filename": file.filename,
            "top_sizes": per_df.head(5).to_dict(orient="records"),
            "total_orders": len(sizes)
        })
        debug_collection.append({"filename": file.filename, "debug": debug_info})

    if not all_sizes:
        return {"top_sizes": [], "total_orders": 0, "per_file": per_file, "top_customers": [], "debug": debug_collection}

    # overall sizes
    df = pd.Series(all_sizes, name="size").value_counts().reset_index()
    df.columns = ["size", "count"]
    top_sizes = df.head(5).to_dict(orient="records")

    # customers aggregation (preserve your original behavior)
    if all_customers:
        customer_counts = pd.Series(all_customers, name="customer").value_counts().reset_index()
        customer_counts.columns = ["customer", "order_count"]
        if len(files) == 1:
            customer_counts = customer_counts[customer_counts["order_count"] >= 1]
        else:
            customer_counts = customer_counts[customer_counts["order_count"] > 1]

        # amounts
        if all_order_amounts:
            df_amt = pd.DataFrame(all_order_amounts, columns=["customer", "amount", "filename"])
            amt_sum = df_amt.groupby("customer")["amount"].sum().reset_index()
            customer_counts = customer_counts.merge(amt_sum, on="customer", how="left")
            customer_counts["amount"] = customer_counts["amount"].fillna(0)
        else:
            customer_counts["amount"] = 0

        # filenames aggreg
        if all_customer_files:
            df_files = pd.DataFrame(all_customer_files, columns=["customer", "filename"])
            file_map = df_files.groupby("customer")["filename"].apply(lambda x: ", ".join(sorted(set(x)))).reset_index()
            customer_counts = customer_counts.merge(file_map, on="customer", how="left")
        else:
            customer_counts["filename"] = ""

        top_customers = customer_counts.head(20).to_dict(orient="records")
    else:
        top_customers = []

    result = {
        "top_sizes": top_sizes,
        "total_orders": len(all_sizes),
        "per_file": per_file,
        "top_customers": top_customers,
        "debug": debug_collection  # <-- use this for inspecting parsing behavior
    }
    return result
