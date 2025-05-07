import pytest
from fastapi.testclient import TestClient
import time
from tracing_bug_bash.app import app, memory_exporter

client = TestClient(app)

def test_spans_collection():
    """
    Test 1: Verify that spans are being collected correctly.
    Currently spans list is empty, but we expect at least 3 spans
    after visiting the root endpoint.
    
    This tests that the span processor and exporter are properly configured.
    """
    # Clear any existing spans
    memory_exporter.clear()
    
    # Make a request to the root endpoint
    response = client.get("/")
    assert response.status_code == 200
    
    # Give the spans some time to be processed
    time.sleep(0.1)
    
    # Check spans endpoint
    spans_response = client.get("/spans")
    assert spans_response.status_code == 200
    
    # Currently this will fail because no spans are being collected
    spans = spans_response.json()["spans"]
    
    # We expect at least 3 spans: 
    # 1. The overall request span from FastAPI instrumentation 
    # 2. The root_endpoint span created in our code
    # 3. The get_spans span created when checking the spans endpoint
    assert len(spans) >= 3, f"Expected at least 3 spans, but got {len(spans)}"
    
    # Verify that our custom span is among the collected spans
    custom_spans = [span for span in spans if span["name"] == "root_endpoint"]
    assert len(custom_spans) > 0, "Custom root_endpoint span not found in collected spans"
    
    # Verify attributes on our custom span
    assert custom_spans[0]["attributes"]["endpoint"] == "root"

def test_error_endpoint():
    """
    Test 2: Verify that the error endpoint is fixed to return 200 instead of 500.
    Currently it always raises an HTTPException with status code 500.
    """
    # This will fail until the endpoint is fixed
    response = client.get("/error")
    
    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    assert "status" in response.json(), "Response JSON should contain 'status' key"
    assert response.json()["status"] == "ok", "Status should be 'ok'"

def test_context_propagation():
    """
    Test 3: Verify that the trace context is properly propagated to downstream services.
    Currently context propagation is broken.
    """
    # Clear any existing spans
    memory_exporter.clear()
    
    # Make a request to the downstream endpoint
    response = client.get("/downstream")
    assert response.status_code == 200
    
    # Extract the result from the downstream response
    downstream_response = response.json()["downstream_response"]
    
    # Currently this will fail because context propagation is not working
    assert downstream_response["context_propagated"], "Trace context was not properly propagated"
    
    # Additional check: the two trace IDs should match
    assert downstream_response["original_trace_id"] == downstream_response["current_trace_id"], \
        "Trace IDs do not match: original={}, current={}".format(
            downstream_response["original_trace_id"],
            downstream_response["current_trace_id"]
        ) 