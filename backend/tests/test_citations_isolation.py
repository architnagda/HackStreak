from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.document import Document
from app.core.security import create_access_token

client = TestClient(app)

def test_citations_isolation_and_no_contamination():
    db = SessionLocal()
    
    user = db.query(User).filter(User.email == "abc@gmail.com").first()
    assert user is not None, "User abc@gmail.com must exist"
    
    docs = db.query(Document).filter(Document.user_id == user.id).all()
    assert len(docs) >= 2, f"User {user.email} should have at least 2 documents"
    
    doc1 = docs[0] # e.g. IKS assignment 1 A.pdf
    doc2 = docs[1] # e.g. lab-submission-format.docx
    doc3 = docs[2] if len(docs) > 2 else docs[0]
    
    doc_map = {d.filename: d.id for d in docs}
    print("User documents:", doc_map)
    
    token = create_access_token(subject=str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # TEST 1: Question specifically about Doc 1 (e.g. IKS assignment 1 A.pdf)
    print(f"\n--- Running TEST 1: Question specifically about Doc 1 ({doc1.filename}) ---")
    res1 = client.post(
        "/api/chat",
        headers=headers,
        json={"question": f"What are the main topics and methods in {doc1.filename}?"}
    )
    assert res1.status_code == 200
    data1 = res1.json()
    conv_id = data1["conversation_id"]
    sources1 = data1["sources"]
    print("Test 1 sources:", [(s["document_name"], s["page_number"]) for s in sources1])
    assert len(sources1) > 0, "Expected citations for Test 1"
    for s in sources1:
        assert s["document_id"] == doc1.id, f"Expected {doc1.filename}, got {s['document_name']}"

    # TEST 2: Question about Doc 2 in the SAME conversation session (no previous source leakage)
    print(f"\n--- Running TEST 2: Question about Doc 2 ({doc2.filename}) in same session ---")
    res2 = client.post(
        "/api/chat",
        headers=headers,
        json={
            "conversation_id": conv_id,
            "question": f"What are the formatting rules and sections in {doc2.filename}?"
        }
    )
    assert res2.status_code == 200
    data2 = res2.json()
    sources2 = data2["sources"]
    print("Test 2 sources:", [(s["document_name"], s["page_number"]) for s in sources2])
    assert len(sources2) > 0, "Expected citations for Test 2"
    # Must contain ONLY doc2, absolutely NO doc1 citations!
    for s in sources2:
        assert s["document_id"] == doc2.id, f"Previous source from Doc 1 leaked into Test 2: {s['document_name']}"

    # TEST 3: Third question about Doc 3 (or Doc 1 again) in same session
    print(f"\n--- Running TEST 3: Third question about Doc 3 ({doc3.filename}) ---")
    res3 = client.post(
        "/api/chat",
        headers=headers,
        json={
            "conversation_id": conv_id,
            "question": f"Summarize key aspects in {doc3.filename}."
        }
    )
    assert res3.status_code == 200
    data3 = res3.json()
    sources3 = data3["sources"]
    print("Test 3 sources:", [(s["document_name"], s["page_number"]) for s in sources3])
    for s in sources3:
        assert s["document_id"] == doc3.id, f"Contamination in Test 3: {s['document_name']}"

    # TEST 4: Follow-up question relying on conversation context
    print("\n--- Running TEST 4: Follow-up question ---")
    res4_init = client.post(
        "/api/chat",
        headers=headers,
        json={"question": f"What is the objective in {doc1.filename}?"}
    )
    assert res4_init.status_code == 200
    conv4_id = res4_init.json()["conversation_id"]

    res4_follow = client.post(
        "/api/chat",
        headers=headers,
        json={
            "conversation_id": conv4_id,
            "question": "When was it submitted and what are the details?"
        }
    )
    assert res4_follow.status_code == 200
    data4 = res4_follow.json()
    sources4 = data4["sources"]
    print("Test 4 sources:", [(s["document_name"], s["page_number"]) for s in sources4])
    for s in sources4:
        assert s["document_id"] == doc1.id, f"Follow-up retrieved wrong doc: {s['document_name']}"

    # TEST 5: Multi-source question comparing Doc 1 and Doc 2
    print(f"\n--- Running TEST 5: Multi-source comparison between {doc1.filename} and {doc2.filename} ---")
    res5 = client.post(
        "/api/chat",
        headers=headers,
        json={"question": f"Compare {doc1.filename} and {doc2.filename}."}
    )
    assert res5.status_code == 200
    data5 = res5.json()
    sources5 = data5["sources"]
    print("Test 5 sources:", [(s["document_name"], s["page_number"]) for s in sources5])
    doc_ids = {s["document_id"] for s in sources5}
    assert (doc1.id in doc_ids) or (doc2.id in doc_ids)

    # TEST 6: Document filter mode (single document selected explicitly)
    print(f"\n--- Running TEST 6: Selected document filter mode ({doc1.filename}) ---")
    res6 = client.post(
        "/api/chat",
        headers=headers,
        json={
            "question": "What is described in this document?",
            "document_ids": [doc1.id]
        }
    )
    assert res6.status_code == 200
    data6 = res6.json()
    sources6 = data6["sources"]
    print("Test 6 sources:", [(s["document_name"], s["page_number"]) for s in sources6])
    assert len(sources6) > 0
    for s in sources6:
        assert s["document_id"] == doc1.id

    # TEST 7: No evidence question (sources must be completely empty)
    print("\n--- Running TEST 7: No evidence question (sources must be empty) ---")
    res7 = client.post(
        "/api/chat",
        headers=headers,
        json={
            "question": "What is the secret recipe for chocolate cake on the moon?",
            "document_ids": [doc1.id]
        }
    )
    assert res7.status_code == 200
    data7 = res7.json()
    print("Test 7 sources count:", len(data7["sources"]))
    assert len(data7["sources"]) == 0, f"Expected 0 sources on insufficient evidence, got {len(data7['sources'])}"
    assert data7["has_insufficient_evidence"] is True

    # Verify message-level database isolation
    print("\n--- Verifying historical message sources isolation from DB ---")
    res_hist = client.get(f"/api/conversations/{conv_id}", headers=headers)
    assert res_hist.status_code == 200
    conv_data = res_hist.json()
    for m in conv_data["messages"]:
        if m["role"] == "assistant":
            print(f"Message #{m['id']} citations: {[(s['document_name'], s['page_number']) for s in m['sources']]}")
            page_keys = [(s['document_name'], s['page_number']) for s in m['sources']]
            assert len(page_keys) == len(set(page_keys)), f"Duplicate page citation found in message #{m['id']}"

    db.close()
    print("\n=== ALL 7 CITATION ISOLATION & DEDUPLICATION TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_citations_isolation_and_no_contamination()
