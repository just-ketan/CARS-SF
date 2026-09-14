import os
import glob
import re

directories = [
    "RSNSD/traffic_generator/healthcare",
    "RSNSD/traffic_generator/education",
    "RSNSD/traffic_generator/agriculture",
    "RSNSD/traffic_generator/general"
]

for d in directories:
    for filepath in glob.glob(os.path.join(d, "*.py")):
        if filepath.endswith("__init__.py") or filepath.endswith("registry.py"):
            continue
            
        with open(filepath, "r") as f:
            content = f.read()
            
        # Check if already patched
        if "expected_user_density=" in content:
            continue
            
        # We need to insert the 4 fields into the ApplicationProfile(...) call
        # Usually it ends with metadata={ ... } or priority=PriorityLevel... 
        
        # We can just insert them right before the closing parenthesis of ApplicationProfile.
        # Let's find the last occurrence of ")" that closes ApplicationProfile.
        
        # A simple string replacement before "metadata={" or before the final ")"
        if "metadata={" in content:
            new_fields = """
    expected_user_density="Medium",
    failure_sensitivity="High",
    burstiness="Moderate",
    traffic_pattern="Continuous",
    metadata={"""
            content = content.replace("metadata={", new_fields)
        else:
            # Find the last closing parenthesis that is on a line by itself or after a comma
            # This is fragile, let's just insert before the last line that matches ")"
            pass
            
        with open(filepath, "w") as f:
            f.write(content)
