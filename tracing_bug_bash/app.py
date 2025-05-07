import os
from fastapi import FastAPI, Request, HTTPException, Depends, Response
from fastapi.responses import JSONResponse
import logging
import requests
import time
import json
from typing import Dict, List, Any

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    BatchSpanProcessor,
    InMemorySpanExporter
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="VectorBench Tracing App")

# Initialize in-memory span exporter for testing
memory_exporter = InMemorySpanExporter()

# BUG 1: Missing span export configuration
# The tracer provider is created but no exporter is attached
# This should be fixed by adding SimpleSpanProcessor with memory_exporter
provider = TracerProvider()
trace.set_tracer_provider(provider)
# MISSING: provider.add_span_processor(SimpleSpanProcessor(memory_exporter))

# Get a tracer from the global TracerProvider
tracer = trace.get_tracer(__name__)

# Initialize FastAPI instrumentation
FastAPIInstrumentor.instrument_app(app)

# In-memory storage for collected spans (used for testing)
collected_spans = []

@app.get("/")
async def root():
    """Root endpoint that returns a welcome message"""
    with tracer.start_as_current_span("root_endpoint") as span:
        span.set_attribute("endpoint", "root")
        return {"message": "Welcome to VectorBench Tracing App"}

@app.get("/error")
async def error_endpoint():
    """
    BUG 2: This endpoint always returns an error (500)
    It should be fixed to return a 200 OK response
    """
    with tracer.start_as_current_span("error_endpoint") as span:
        span.set_attribute("endpoint", "error")
        
        # Simulate some processing
        time.sleep(0.1)
        
        # BUG: This always raises an error
        # Should be fixed to return a normal response
        raise HTTPException(status_code=500, detail="Internal Server Error")
        # CORRECT: return {"status": "ok"}

@app.get("/downstream")
async def call_downstream():
    """
    Calls a downstream service and returns the result
    BUG 3: The context propagation is broken
    """
    with tracer.start_as_current_span("downstream_request") as span:
        span.set_attribute("endpoint", "downstream")
        
        # Get the current context
        current_context = trace.get_current_span().get_span_context()
        
        # BUG: We're not propagating the trace context to the downstream service
        # The headers should contain the trace context
        headers = {
            "Content-Type": "application/json",
            # MISSING: TraceContextTextMapPropagator().inject(headers)
        }
        
        # Call the echo endpoint which simulates a downstream service
        response = requests.get(
            f"http://localhost:8000/echo/{current_context.trace_id:032x}",
            headers=headers
        )
        
        return {"downstream_response": response.json()}

@app.get("/echo/{trace_id}")
async def echo(trace_id: str):
    """Echo endpoint that simulates a downstream service"""
    with tracer.start_as_current_span("echo_service") as span:
        span.set_attribute("endpoint", "echo")
        
        # Get the current context after span creation
        current_context = trace.get_current_span().get_span_context()
        current_trace_id = f"{current_context.trace_id:032x}"
        
        # Return both trace IDs for comparison
        return {
            "original_trace_id": trace_id,
            "current_trace_id": current_trace_id,
            "context_propagated": trace_id == current_trace_id
        }

@app.get("/spans")
async def get_spans():
    """
    Returns all collected spans for inspection
    This is used in testing to verify tracing is working
    """
    # BUG: We can't get the spans because we never attached the exporter
    spans = memory_exporter.get_finished_spans()
    memory_exporter.clear()
    
    # Convert spans to a simple dictionary for JSON serialization
    simplified_spans = []
    for span in spans:
        span_dict = {
            "name": span.name,
            "trace_id": f"{span.context.trace_id:032x}",
            "span_id": f"{span.context.span_id:016x}",
            "parent_id": f"{span.parent.span_id:016x}" if span.parent else None,
            "attributes": dict(span.attributes),
            "status": str(span.status),
            "kind": str(span.kind),
        }
        simplified_spans.append(span_dict)
    
    return {"spans": simplified_spans}

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy"} 