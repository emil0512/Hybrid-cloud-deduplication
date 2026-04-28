import os
import re
import logging

logger = logging.getLogger(__name__)

def scan_file_content(file_content, original_filename):
    """
    Scans ALL files but ONLY blocks real threats
    """
    threats = []
    is_safe = True
    
    print(f"SCAN_FUNCTION CALLED for: {original_filename}")  # DEBUG
    
    # Get file extension
    extension = os.path.splitext(original_filename)[1].lower()
    print(f"File extension: {extension}")  # DEBUG
    
    try:
        # Try to read as text
        content_str = file_content.decode('utf-8', errors='ignore').lower()
        print(f"Content length: {len(content_str)} characters")  # DEBUG
        
        # Check for PHP webshell pattern
        if 'eval($_post' in content_str or 'eval($_get' in content_str:
            threats.append("PHP webshell detected (eval)")
            is_safe = False
            print("THREAT: PHP webshell detected")  # DEBUG
        
        # Check for base64 decode pattern
        if 'base64_decode($_post' in content_str or 'base64_decode($_get' in content_str:
            threats.append("Base64 encoded payload detected")
            is_safe = False
            print("THREAT: Base64 payload detected")  # DEBUG
        
        # Check for system command pattern
        if 'system($_get' in content_str or 'shell_exec($_get' in content_str:
            threats.append("System command execution detected")
            is_safe = False
            print("THREAT: System command detected")  # DEBUG
        
        # Check for wget/curl command injection
        if '; wget http://' in content_str or '; curl http://' in content_str:
            threats.append("Command injection detected (wget/curl)")
            is_safe = False
            print("THREAT: Command injection detected")  # DEBUG
        
        # Check for SQL injection patterns
        if 'union select' in content_str and 'from' in content_str:
            threats.append("SQL injection pattern detected")
            is_safe = False
            print("THREAT: SQL injection detected")  # DEBUG
        
        # Check for remote file inclusion
        if 'include("http://' in content_str or 'require("http://' in content_str:
            threats.append("Remote file inclusion detected")
            is_safe = False
            print("THREAT: Remote file inclusion detected")  # DEBUG
        
        if is_safe:
            print(f"FILE IS SAFE: {original_filename}")  # DEBUG
            
    except UnicodeDecodeError:
        # Binary file - always safe
        print(f"Binary file (safe): {original_filename}")  # DEBUG
        is_safe = True
        threats = []
        
    except Exception as e:
        print(f"SCAN ERROR: {e}")  # DEBUG
        is_safe = True
    
    print(f"Returning - is_safe: {is_safe}, threats: {threats}")  # DEBUG
    return is_safe, threats