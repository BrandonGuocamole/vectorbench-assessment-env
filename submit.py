#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
import tempfile
import time
import datetime
import re
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Collect environment variables (or use defaults)
SUPABASE_PROJECT_URL = os.environ.get("SUPABASE_PROJECT_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_USER_JWT = os.environ.get("SUPABASE_USER_JWT", "")
ASSESSMENT_ID = os.environ.get("ASSESSMENT_ID", "tracing_bug_bash_v1")
CODESPACE_NAME = os.environ.get("CODESPACE_NAME", "")

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_banner(message: str, color: str = GREEN) -> None:
    """Print a colored banner message."""
    separator = "=" * (len(message) + 4)
    print(f"\n{color}{separator}")
    print(f"| {message} |")
    print(f"{separator}{RESET}\n")

def run_tests() -> bool:
    """Run the tests and return True if all tests pass."""
    print_banner("Running tests...", YELLOW)
    
    # Run pytest with quiet flag
    result = subprocess.run(["pytest", "-q"], capture_output=True, text=True)
    
    # Print the output
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result.returncode == 0

def parse_log_for_runtime() -> Tuple[int, Optional[datetime.datetime], Optional[datetime.datetime]]:
    """
    Parse the VectorBench log file to calculate runtime.
    Returns:
        Tuple of (runtime_seconds, start_time, end_time)
    """
    print("Checking log file for runtime data...")
    
    try:
        log_path = Path(".vb_log")
        if not log_path.exists():
            print(f"{YELLOW}Warning: .vb_log file not found. Runtime data unavailable.{RESET}")
            return 0, None, None
        
        log_content = log_path.read_text()
        
        # Extract timestamps using regex
        timestamps = re.findall(r'([\w]{3} [\w]{3} \d{1,2} \d{2}:\d{2}:\d{2} [\w]{3} \d{4})', log_content)
        
        if len(timestamps) < 2:
            print(f"{YELLOW}Warning: Not enough timestamps in log. Runtime data may be inaccurate.{RESET}")
            return 0, None, None
        
        # Parse the first and last timestamps
        start_time = datetime.datetime.strptime(timestamps[0], "%a %b %d %H:%M:%S %Z %Y")
        end_time = datetime.datetime.strptime(timestamps[-1], "%a %b %d %H:%M:%S %Z %Y")
        
        # Calculate runtime in seconds
        runtime_seconds = int((end_time - start_time).total_seconds())
        
        print(f"Calculated assessment runtime: {runtime_seconds} seconds")
        return runtime_seconds, start_time, end_time
    
    except Exception as e:
        print(f"{YELLOW}Warning: Error parsing log file: {e}{RESET}")
        return 0, None, None

def generate_upload_url() -> Dict[str, str]:
    """
    Call the Supabase Edge Function to generate a presigned URL for upload.
    Returns:
        Dict with presignedUrl and actualStoragePath.
    """
    if not all([SUPABASE_PROJECT_URL, SUPABASE_ANON_KEY, SUPABASE_USER_JWT]):
        print(f"{RED}Error: Missing Supabase configuration. Unable to generate upload URL.{RESET}")
        print(f"SUPABASE_PROJECT_URL: {'Set' if SUPABASE_PROJECT_URL else 'Not Set'}")
        print(f"SUPABASE_ANON_KEY: {'Set' if SUPABASE_ANON_KEY else 'Not Set'}")
        print(f"SUPABASE_USER_JWT: {'Set' if SUPABASE_USER_JWT else 'Not Set'}")
        return {"presignedUrl": "", "actualStoragePath": ""}
    
    print("Generating upload URL from Supabase...")
    
    edge_function_url = f"{SUPABASE_PROJECT_URL}/functions/v1/generate_upload_url"
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_USER_JWT}",
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }
    
    # Generate a filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"submission-{timestamp}.zip"
    
    try:
        response = requests.post(
            edge_function_url,
            headers=headers,
            json={"filename": filename}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"{RED}Error generating upload URL: {e}{RESET}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response content: {e.response.content.decode()}")
        return {"presignedUrl": "", "actualStoragePath": ""}

def create_submission_zip() -> str:
    """
    Create a zip file of the workspace for submission.
    Returns:
        Path to the created zip file.
    """
    print("Creating submission zip file...")
    
    # Create a temporary directory for the zip
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "submission.zip")
    
    try:
        # List of directories and files to exclude
        exclude_patterns = [
            ".git",
            "__pycache__",
            "*.pyc",
            ".venv",
            ".devcontainer",
            "node_modules",
            ".pytest_cache"
        ]
        
        # Build the zip command with exclusions
        exclude_args = []
        for pattern in exclude_patterns:
            exclude_args.extend(["-x", f"*{pattern}*"])
        
        # Create the zip file using the zip command
        # The -r flag makes it recursive
        subprocess.run(
            ["zip", "-r", zip_path, "."] + exclude_args,
            check=True,
            capture_output=True
        )
        
        zip_size = os.path.getsize(zip_path) / (1024 * 1024)  # Size in MB
        print(f"Created submission zip ({zip_size:.2f} MB): {zip_path}")
        return zip_path
    
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error creating zip file: {e}{RESET}")
        print(f"Stdout: {e.stdout.decode() if e.stdout else 'None'}")
        print(f"Stderr: {e.stderr.decode() if e.stderr else 'None'}")
        return ""

def upload_to_supabase(zip_path: str, presigned_url: str) -> bool:
    """
    Upload the zip file to Supabase Storage using the presigned URL.
    Returns:
        True if upload was successful, False otherwise.
    """
    if not zip_path or not presigned_url:
        print(f"{RED}Error: Missing zip path or presigned URL for upload.{RESET}")
        return False
    
    print("Uploading submission to Supabase...")
    
    try:
        with open(zip_path, "rb") as f:
            response = requests.put(
                presigned_url,
                data=f,
                headers={"Content-Type": "application/zip"}
            )
            response.raise_for_status()
        
        print(f"{GREEN}Upload successful!{RESET}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"{RED}Error uploading submission: {e}{RESET}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response content: {e.response.content.decode()}")
        return False

def record_submission_in_supabase(runtime: int, status: str, log_path: str) -> bool:
    """
    Record the submission metadata in Supabase using the Edge Function.
    Returns:
        True if the recording was successful, False otherwise.
    """
    if not all([SUPABASE_PROJECT_URL, SUPABASE_ANON_KEY, SUPABASE_USER_JWT]):
        print(f"{RED}Error: Missing Supabase configuration. Unable to record submission.{RESET}")
        return False
    
    print("Recording submission metadata in Supabase...")
    
    edge_function_url = f"{SUPABASE_PROJECT_URL}/functions/v1/record_submission_metadata"
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_USER_JWT}",
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "assessmentId": ASSESSMENT_ID,
        "runtimeSeconds": runtime,
        "status": status,
        "logPathInStorage": log_path
    }
    
    try:
        response = requests.post(
            edge_function_url,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        print(f"{GREEN}Submission metadata recorded successfully!{RESET}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"{RED}Error recording submission metadata: {e}{RESET}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response content: {e.response.content.decode()}")
        return False

def cleanup_codespace() -> None:
    """Clean up the Codespace if self-destruct is enabled."""
    if not CODESPACE_NAME:
        print(f"{YELLOW}Warning: CODESPACE_NAME not set. Skipping self-destruct.{RESET}")
        return
    
    print_banner("Assessment complete! Cleaning up...", GREEN)
    print("This Codespace will be deleted in 30 seconds.")
    print(f"{YELLOW}Press Ctrl+C now if you want to prevent deletion.{RESET}")
    
    try:
        time.sleep(30)
        
        # Use GitHub CLI to delete the Codespace
        subprocess.run(
            ["gh", "api", "-X", "DELETE", f"/user/codespaces/{CODESPACE_NAME}"],
            check=True
        )
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Codespace deletion cancelled by user.{RESET}")
    except Exception as e:
        print(f"{RED}Error during Codespace cleanup: {e}{RESET}")

def main() -> int:
    """Main function that orchestrates the submission process."""
    print_banner("VectorBench Submission Process", BOLD + GREEN)
    
    # 1. Run tests and check if they pass
    tests_pass = run_tests()
    status = "passed" if tests_pass else "failed"
    
    # 2. Parse the log file for runtime data
    runtime, start_time, end_time = parse_log_for_runtime()
    
    # 3. Generate upload URL from Supabase
    url_data = generate_upload_url()
    presigned_url = url_data.get("presignedUrl", "")
    storage_path = url_data.get("actualStoragePath", "")
    
    # If we couldn't get a presigned URL, show the result and exit
    if not presigned_url:
        print(f"\n{RED}Error: Unable to generate upload URL. Submission process aborted.{RESET}")
        print(f"\n{BOLD}Assessment Results:{RESET}")
        print(f"  Status: {'PASS' if tests_pass else 'FAIL'}")
        print(f"  Runtime: {runtime} seconds")
        return 1
    
    # 4. Create submission zip
    zip_path = create_submission_zip()
    if not zip_path:
        print(f"\n{RED}Error: Failed to create submission zip. Submission process aborted.{RESET}")
        return 1
    
    # 5. Upload zip to Supabase Storage
    upload_success = upload_to_supabase(zip_path, presigned_url)
    if not upload_success:
        print(f"\n{RED}Error: Failed to upload submission. Submission process aborted.{RESET}")
        return 1
    
    # 6. Record submission metadata
    record_success = record_submission_in_supabase(runtime, status, storage_path)
    
    # 7. Show final result
    if tests_pass:
        print_banner("🎉 All tests pass! Submission successful!", GREEN)
    else:
        print_banner("❌ Tests failing. Submission recorded for review.", RED)
    
    print(f"{BOLD}Assessment Details:{RESET}")
    print(f"  Status: {'PASS' if tests_pass else 'FAIL'}")
    print(f"  Runtime: {runtime} seconds")
    
    # 8. Clean up temp files
    if os.path.exists(zip_path):
        temp_dir = os.path.dirname(zip_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # 9. Self-destruct Codespace if enabled
    if tests_pass and record_success:
        cleanup_codespace()
    
    return 0 if tests_pass else 1

if __name__ == "__main__":
    sys.exit(main()) 