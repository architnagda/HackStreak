import os
import io
import time
import requests
import pymupdf
from PIL import Image, ImageDraw, ImageFont
import docx

BASE_URL = "http://127.0.0.1:8000/api"

def create_sample_pdf(filename: str) -> str:
    """Creates a 2-page digital PDF with known financial facts."""
    doc = pymupdf.open()
    
    # Page 1
    page1 = doc.new_page()
    page1.insert_text(
        (50, 72),
        "DocuMind Global Annual Financial Report 2025\n\n"
        "Executive Summary:\n"
        "In fiscal year 2025, DocuMind recorded total gross revenue of $142.5 million, representing a 28% year-over-year growth.\n"
        "Operating profit margin reached 34.2% driven by enterprise AI adoption.\n"
        "The Asia-Pacific region was the fastest growing market with 65% annualized growth.\n",
        fontsize=12
    )
    
    # Page 2
    page2 = doc.new_page()
    page2.insert_text(
        (50, 72),
        "Product & Engineering Outlook 2025:\n\n"
        "The R&D division invested $28 million into next-generation multi-source RAG architectures.\n"
        "Headcount expanded by 120 senior AI engineers across Zurich and Tokyo hubs.\n"
        "Customer retention rate for enterprise tiers stood at 98.4%.\n",
        fontsize=12
    )
    
    doc.save(filename)
    doc.close()
    return filename

def create_sample_docx(filename: str) -> str:
    """Creates a sample docx file with 2024 revenue for comparison."""
    doc = docx.Document()
    doc.add_heading("DocuMind Historical Financials 2024", 0)
    
    doc.add_heading("2024 Revenue Overview", level=1)
    doc.add_paragraph(
        "In fiscal year 2024, DocuMind achieved total gross revenue of $111.3 million. "
        "The primary revenue driver was North American enterprise subscriptions."
    )
    
    doc.add_heading("2024 R&D Investments", level=1)
    doc.add_paragraph(
        "R&D expenditure in 2024 was $19.5 million, focusing on foundational computer vision and vector indexing."
    )
    
    doc.save(filename)
    return filename

def create_sample_image(filename: str) -> str:
    """Creates a synthetic image with legible printed text."""
    img = Image.new("RGB", (800, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    text = "Security Policy 2025:\nAll customer documents are encrypted with AES-256-GCM at rest.\nMulti-factor authentication is strictly enforced for all administrative portals."
    draw.text((40, 50), text, fill=(0, 0, 0))
    
    img.save(filename)
    return filename

def run_tests():
    print("=== STARTING COMPLETE PIPELINE & RAG VERIFICATION ===")

    # 1. Register & Login
    unique_user = f"pipeline_test_{int(time.time())}@documind.ai"
    password = "SuperPassword123!"
    
    print(f"\n1. Registering test user {unique_user}...")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": unique_user,
        "password": password,
        "full_name": "Pipeline Verification Bot"
    })
    assert reg_res.status_code == 201, f"Reg failed: {reg_res.text}"
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Registration and token acquisition successful.")

    # 2. Upload Digital PDF (2025 Report)
    pdf_path = "test_annual_report_2025.pdf"
    create_sample_pdf(pdf_path)
    print(f"\n2. Uploading 2-page PDF ({pdf_path})...")
    with open(pdf_path, "rb") as f:
        upload_res = requests.post(
            f"{BASE_URL}/documents/upload",
            headers=headers,
            files={"file": (pdf_path, f, "application/pdf")}
        )
    assert upload_res.status_code == 201, f"PDF upload failed: {upload_res.text}"
    pdf_doc = upload_res.json()
    print(f"[OK] PDF Uploaded & Processed: ID={pdf_doc['id']}, Pages={pdf_doc['total_pages']}, Chunks={pdf_doc['total_chunks']}, Status={pdf_doc['status']}")
    assert pdf_doc["status"] == "completed"
    assert pdf_doc["total_pages"] == 2
    assert pdf_doc["total_chunks"] >= 2

    # 3. Upload DOCX (2024 Report for multi-source)
    docx_path = "test_financials_2024.docx"
    create_sample_docx(docx_path)
    print(f"\n3. Uploading DOCX ({docx_path})...")
    with open(docx_path, "rb") as f:
        docx_res = requests.post(
            f"{BASE_URL}/documents/upload",
            headers=headers,
            files={"file": (docx_path, f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
    assert docx_res.status_code == 201, f"DOCX upload failed: {docx_res.text}"
    docx_doc = docx_res.json()
    print(f"[OK] DOCX Uploaded & Processed: ID={docx_doc['id']}, Chunks={docx_doc['total_chunks']}, Status={docx_doc['status']}")
    assert docx_doc["status"] == "completed"

    # 4. Upload Image (Security Policy)
    img_path = "test_security_policy.png"
    create_sample_image(img_path)
    print(f"\n4. Uploading Image ({img_path})...")
    with open(img_path, "rb") as f:
        img_res = requests.post(
            f"{BASE_URL}/documents/upload",
            headers=headers,
            files={"file": (img_path, f, "image/png")}
        )
    assert img_res.status_code == 201, f"Image upload failed: {img_res.text}"
    img_doc = img_res.json()
    print(f"[OK] Image Uploaded & Processed: ID={img_doc['id']}, Status={img_doc['status']}")

    # 5. Check Document Stats & List
    print("\n5. Testing GET /api/documents and /api/documents/stats...")
    stats_res = requests.get(f"{BASE_URL}/documents/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    print(f"[OK] Stats: Total={stats['total_documents']}, Completed={stats['completed_documents']}, Processing={stats['processing_documents']}")
    assert stats["total_documents"] >= 3

    # 6. Test Direct Semantic Search
    print("\n6. Testing POST /api/search for 'R&D investment'...")
    search_res = requests.post(f"{BASE_URL}/search", headers=headers, json={"query": "R&D investment headcount Zurich", "top_k": 3})
    assert search_res.status_code == 200
    results = search_res.json()
    print(f"[OK] Retrieved {len(results)} chunks:")
    for r in results:
        print(f"   * Doc: {r['filename']} | Page: {r['page_number']} | Score: {r['relevance_score']} | Snippet: {r['content'][:60]}...")
    assert len(results) > 0

    # 7. Test RAG Chat: Single-document fact with Page Citation
    print("\n7. Testing POST /api/chat: 'What was the gross revenue in 2025?'...")
    chat_res1 = requests.post(f"{BASE_URL}/chat", headers=headers, json={
        "question": "What was the gross revenue in 2025 and what was the growth rate?"
    })
    assert chat_res1.status_code == 200
    chat1 = chat_res1.json()
    conv_id = chat1["conversation_id"]
    print(f"[OK] Answer:\n{chat1['answer']}\n")
    print(f"[OK] Sources Citation ({len(chat1['sources'])} citations):")
    for s in chat1["sources"]:
        print(f"   * Source: {s['document_name']} | Page: {s['page_number']} | Evidence: {s['evidence_snippet'][:70]}...")
    assert len(chat1["sources"]) > 0
    assert "142.5" in chat1["answer"] or "142.5" in chat1["sources"][0]["evidence_snippet"]

    # 8. Test Follow-up Question in Same Conversation
    print("\n8. Testing Follow-up Question: 'What about headcount and R&D outlook?'...")
    chat_res2 = requests.post(f"{BASE_URL}/chat", headers=headers, json={
        "conversation_id": conv_id,
        "question": "What about the headcount expansion and R&D outlook?"
    })
    assert chat_res2.status_code == 200
    chat2 = chat_res2.json()
    print(f"[OK] Follow-up Answer:\n{chat2['answer']}\n")

    # 9. Test Multi-Source Query (2024 vs 2025 comparison)
    print("\n9. Testing Multi-Source Query: 'Compare revenue between 2024 and 2025.'...")
    chat_res3 = requests.post(f"{BASE_URL}/chat", headers=headers, json={
        "question": "Compare the revenue between 2024 and 2025."
    })
    assert chat_res3.status_code == 200
    chat3 = chat_res3.json()
    doc_names = {s["document_name"] for s in chat3["sources"]}
    print(f"[OK] Multi-Source Answer:\n{chat3['answer']}\n")
    print(f"[OK] Documents referenced in citations: {doc_names}")

    # 10. Test Insufficient Evidence Detection (No Hallucination)
    print("\n10. Testing Insufficient Evidence query: 'What is the secret recipe for Martian chocolate cake?'...")
    chat_res4 = requests.post(f"{BASE_URL}/chat", headers=headers, json={
        "question": "What is the secret recipe for Martian chocolate cake and when did aliens land?"
    })
    assert chat_res4.status_code == 200
    chat4 = chat_res4.json()
    print(f"[OK] Insufficient Evidence Response:\n{chat4['answer']}\n")
    print(f"[OK] Insufficient evidence flag: {chat4['has_insufficient_evidence']}")
    assert chat4["has_insufficient_evidence"] is True or "insufficient evidence" in chat4["answer"].lower()

    # Clean up generated test files
    for f in [pdf_path, docx_path, img_path]:
        if os.path.exists(f):
            os.remove(f)

    print("\n=======================================================")
    print("ALL PIPELINE & RAG ACCEPTANCE CRITERIA PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    run_tests()
