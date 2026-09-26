from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.document import Document
from app.core.security import create_access_token

client = TestClient(app)

def test_all_seven_retrieval_cases():
    db = SessionLocal()
    
    # 1. Setup user 8 (abc@gmail.com) and verify documents
    user = db.query(User).filter(User.email == "abc@gmail.com").first()
    assert user is not None, "User abc@gmail.com must exist"
    
    user_docs = db.query(Document).filter(Document.user_id == user.id).all()
    assert len(user_docs) >= 2, f"User {user.email} should have at least 2 documents"
    
    doc1 = user_docs[0] # e.g. SE exp 8 A.pdf
    doc2 = user_docs[1] # e.g. SE 5 A1.pdf
    
    # Find a document belonging to another user for security test
    other_doc = db.query(Document).filter(Document.user_id != user.id).first()
    assert other_doc is not None, "A document from another user must exist for security testing"
    
    # Generate auth token for user 8
    token = create_access_token(subject=str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n--- Testing with user={user.email} (id={user.id}) ---")
    print(f"User docs: {doc1.id} ({doc1.filename}), {doc2.id} ({doc2.filename})")
    print(f"Other user doc: {other_doc.id} ({other_doc.filename}, owner={other_doc.user_id})")

    # TEST 1: Default All Documents Mode (document_ids omitted or empty)
    print("\n--- Running TEST 1: Default All Documents ---")
    res1 = client.post(
        "/api/chat",
        headers=headers,
        json={"question": "What are the main topics discussed across all documents?"}
    )
    assert res1.status_code == 200, f"Test 1 failed: {res1.text}"
    data1 = res1.json()
    print("Test 1 response:", data1["answer"][:120], "...")
    print("Test 1 source count:", len(data1["sources"]))
    assert "answer" in data1
    conv_id = data1["conversation_id"]

    # TEST 2: Single Document Mode
    print(f"\n--- Running TEST 2: Single Document ({doc1.filename}) ---")
    res2 = client.post(
        "/api/chat",
        headers=headers,
        json={
            "question": "What are the details mentioned here?",
            "document_ids": [doc1.id]
        }
    )
    assert res2.status_code == 200, f"Test 2 failed: {res2.text}"
    data2 = res2.json()
    for src in data2["sources"]:
        assert src["document_id"] == doc1.id, f"Source doc {src['document_id']} should match {doc1.id}"
    print(f"Test 2 passed: All {len(data2['sources'])} sources strictly match doc_id={doc1.id}")

    # TEST 3: Multiple Documents Mode
    print(f"\n--- Running TEST 3: Multiple Documents ({doc1.id}, {doc2.id}) ---")
    res3 = client.post(
        "/api/chat",
        headers=headers,
        json={
            "question": "Compare the key findings between these files.",
            "document_ids": [doc1.id, doc2.id]
        }
    )
    assert res3.status_code == 200, f"Test 3 failed: {res3.text}"
    data3 = res3.json()
    allowed_ids = {doc1.id, doc2.id}
    for src in data3["sources"]:
        assert src["document_id"] in allowed_ids, f"Source doc {src['document_id']} not in allowed set {allowed_ids}"
    print(f"Test 3 passed: All {len(data3['sources'])} sources belong strictly to selected doc_ids {allowed_ids}")

    # TEST 4: Missing Evidence in Selected Document
    print("\n--- Running TEST 4: Missing Evidence in Selected Document ---")
    res4 = client.post(
        "/api/chat",
        headers=headers,
        json={
            "question": "What is the secret recipe for chocolate cake on the planet Jupiter?",
            "document_ids": [doc1.id]
        }
    )
    assert res4.status_code == 200, f"Test 4 failed: {res4.text}"
    data4 = res4.json()
    assert "insufficient evidence" in data4["answer"].lower(), "Expected insufficient evidence statement"
    assert "selected documents" in data4["answer"].lower() or data4.get("has_insufficient_evidence") is True
    print(f"Test 4 passed: Strict insufficient evidence returned: {data4['answer'][:100]}...")

    # TEST 5: Switch Back to All Documents Mode
    print("\n--- Running TEST 5: Switch Back to All Documents ---")
    res5 = client.post(
        "/api/chat",
        headers=headers,
        json={
            "question": "Summarize all experiments.",
            "document_ids": []
        }
    )
    assert res5.status_code == 200, f"Test 5 failed: {res5.text}"
    data5 = res5.json()
    print("Test 5 passed: All-docs retrieval succeeded, sources:", len(data5["sources"]))

    # TEST 6: Follow-up Question in Session
    print("\n--- Running TEST 6: Follow-up Scoped to Document ---")
    res6_1 = client.post(
        "/api/chat",
        headers=headers,
        json={
            "question": "What is the objective of this experiment?",
            "document_ids": [doc1.id]
        }
    )
    assert res6_1.status_code == 200
    conv6_id = res6_1.json()["conversation_id"]

    res6_2 = client.post(
        "/api/chat",
        headers=headers,
        json={
            "conversation_id": conv6_id,
            "question": "And what methodology was used?",
            "document_ids": [doc1.id]
        }
    )
    assert res6_2.status_code == 200
    data6_2 = res6_2.json()
    assert data6_2["conversation_id"] == conv6_id
    for src in data6_2["sources"]:
        assert src["document_id"] == doc1.id
    print(f"Test 6 passed: Follow-up in conv {conv6_id} stayed scoped to doc {doc1.id}")

    # TEST 7: Security - Attempt to Access Another User's Document ID
    print(f"\n--- Running TEST 7: Security Ownership Verification for Doc #{other_doc.id} ---")
    res7 = client.post(
        "/api/chat",
        headers=headers,
        json={
            "question": "Tell me the confidential contents of this file.",
            "document_ids": [other_doc.id]
        }
    )
    assert res7.status_code == 403, f"Expected 403 Forbidden, got {res7.status_code}: {res7.text}"
    print("Test 7 passed: Unauthorized document access was blocked with 403 Forbidden!")
    
    db.close()
    print("\n=== ALL 7 RETRIEVAL & FILTERING TEST CASES PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_all_seven_retrieval_cases()
