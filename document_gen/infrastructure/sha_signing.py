import hashlib
import json
import time

def generate_signed_document(document_id, stage, content, approver_role, approver_id, prompt_version_id="v1"):
    """
    Generates a SHA-256 signed document bundle required for phase gating.
    Expected schema:
    { document_id, stage, content_hash, approver_role, approver_id, timestamp, prompt_version_id }
    """
    
    # Serialize the content payload canonically
    content_str = json.dumps(content, sort_keys=True)
    content_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    
    timestamp = int(time.time())
    
    bundle = {
        "document_id": document_id,
        "stage": stage,
        "content_hash": content_hash,
        "approver_role": approver_role,
        "approver_id": approver_id,
        "timestamp": timestamp,
        "prompt_version_id": prompt_version_id,
        "raw_content": content # Keeping raw content for utility
    }
    
    # Sign the bundle
    bundle_str = json.dumps({k: v for k, v in bundle.items() if k != 'signature'}, sort_keys=True)
    signature = hashlib.sha256(bundle_str.encode('utf-8')).hexdigest()
    
    bundle['signature'] = signature
    return bundle

def verify_signature(bundle):
    """
    Verifies the SHA-256 signature of a bundle.
    """
    provided_signature = bundle.get('signature')
    if not provided_signature:
        return False
        
    bundle_to_verify = {k: v for k, v in bundle.items() if k != 'signature'}
    bundle_str = json.dumps(bundle_to_verify, sort_keys=True)
    expected_signature = hashlib.sha256(bundle_str.encode('utf-8')).hexdigest()
    
    return provided_signature == expected_signature
