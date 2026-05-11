#!/usr/bin/env python3
"""
Verification script for cloud deployment data loading
Run this after Render services have fully deployed
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "https://ia-reto-agent.onrender.com"
INFLUENCE_URL = "https://influence-mcp.onrender.com"

def check_service(url, name):
    """Check if a service is healthy and has data"""
    try:
        resp = requests.get(f"{url}/health", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        print(f"  {name}: OK")
        if 'dataset' in data and 'rows' in data['dataset']:
            print(f"    - Dataset: {data['dataset']['rows']:,} rows")
        return True
    except Exception as e:
        print(f"  {name}: NOT READY ({str(e)[:40]})")
        return False

def test_agent_with_data():
    """Test agent to see if it's getting real data from MCPs"""
    print("\n[3] Testing Agent Responses...")

    query = "Cuales son los 3 usuarios mas influyentes?"
    payload = {"query": query}

    try:
        resp = requests.post(f"{BASE_URL}/chat", json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        response_text = data.get('response', '')
        tool_used = data.get('tool_used', 'unknown')

        print(f"  Query: {query}")
        print(f"  Tool called: {tool_used}")

        # Check if response has actual data (look for author names)
        has_data = any(name in response_text for name in ['Grok', 'Noticias', 'Merryluz'])

        if has_data:
            print("  Result: REAL DATA DETECTED")
            print(f"  Response preview: {response_text[:200]}...")
        else:
            print("  Result: NO REAL DATA (MCPs still loading)")
            print(f"  Response: {response_text[:150]}...")

    except Exception as e:
        print(f"  Error: {str(e)}")

def main():
    print("\n" + "="*70)
    print("CLOUD DEPLOYMENT VERIFICATION")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n[1] Service Health Check...")
    agent_ok = check_service(BASE_URL, "Agent (ia-reto-agent)")
    influence_ok = check_service(INFLUENCE_URL, "Influence MCP")

    if not agent_ok:
        print("\n[ERROR] Agent not healthy. Check Render dashboard.")
        return

    print("\n[2] Agent Status...")
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=5)
        data = resp.json()
        print(f"  Provider: {data.get('provider', '?')}")
        print(f"  Version: {data.get('version', '?')}")
    except:
        pass

    if influence_ok:
        test_agent_with_data()
    else:
        print("\n[3] Testing Agent Responses...")
        print("  Influence MCP not ready yet - will test when deployed")
        test_agent_with_data()

    print("\n" + "="*70)
    print("VERIFICATION COMPLETE")
    print("="*70)
    print("\nIf MCPs show as NOT READY:")
    print("  - Wait 2-3 more minutes for Render to initialize")
    print("  - Check Render dashboard for deployment logs")
    print("  - Verify parquet file deployed with: git log --oneline | head -5")

if __name__ == "__main__":
    main()
