"""Helper utilities for SAP Document AI demo."""

import json


def display_capabilities(capabilities):
    """Print available document types and extraction fields in a readable format."""
    print("=== Document AI capabilities ===\n")
    if isinstance(capabilities, dict):
        print(json.dumps(capabilities, indent=2))
    else:
        print(capabilities)
    print()
