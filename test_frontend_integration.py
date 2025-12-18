#!/usr/bin/env python3
"""
Test Frontend-Backend Integration

Verifies that:
1. Backend APIs are accessible
2. Data is properly formatted
3. Frontend can consume the APIs
"""

import requests
import json

BACKEND_URL = "http://localhost:8000"

def test_officers_api():
    """Test Officers API endpoint"""
    print("\n=== Testing Officers API ===")
    url = f"{BACKEND_URL}/api/officers/?page=1&page_size=3"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        print(f"✓ Status: {response.status_code}")
        print(f"✓ Total officers: {data['total']}")
        print(f"✓ Page: {data['page']}")
        print(f"✓ Returned {len(data['officers'])} officers")

        if data['officers']:
            officer = data['officers'][0]
            print(f"\nSample Officer:")
            print(f"  - Name: {officer['name']}")
            print(f"  - Position: {officer.get('position', 'N/A')}")
            print(f"  - Company: {officer.get('company_name', 'N/A')}")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_convertible_bonds_api():
    """Test Convertible Bonds API endpoint"""
    print("\n=== Testing Convertible Bonds API ===")
    url = f"{BACKEND_URL}/api/convertible-bonds/?page=1&page_size=3"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        print(f"✓ Status: {response.status_code}")
        print(f"✓ Total bonds: {data['total']}")
        print(f"✓ Page: {data['page']}")
        print(f"✓ Returned {len(data['bonds'])} bonds")

        if data['bonds']:
            bond = data['bonds'][0]
            print(f"\nSample Bond:")
            print(f"  - Name: {bond['bond_name']}")
            print(f"  - Company: {bond.get('company_name', 'N/A')}")
            print(f"  - Issue Amount: {bond.get('issue_amount', 'N/A')}")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_cb_subscribers_api():
    """Test CB Subscribers API endpoint"""
    print("\n=== Testing CB Subscribers API ===")
    url = f"{BACKEND_URL}/api/cb-subscribers/?page=1&page_size=3"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        print(f"✓ Status: {response.status_code}")
        print(f"✓ Total subscribers: {data['total']}")
        print(f"✓ Page: {data['page']}")
        print(f"✓ Returned {len(data['subscribers'])} subscribers")

        if data['subscribers']:
            subscriber = data['subscribers'][0]
            print(f"\nSample Subscriber:")
            print(f"  - Name: {subscriber['subscriber_name']}")
            print(f"  - Bond: {subscriber.get('bond_name', 'N/A')}")
            print(f"  - Amount: {subscriber.get('subscription_amount', 'N/A')}")
            print(f"  - Related Party: {subscriber.get('is_related_party', False)}")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_company_specific_data():
    """Test getting data for a specific company"""
    print("\n=== Testing Company-Specific Data ===")

    # First, get a company ID
    try:
        response = requests.get(f"{BACKEND_URL}/api/companies/search?page_size=1")
        response.raise_for_status()
        companies = response.json()

        if not companies.get('companies'):
            print("✗ No companies found")
            return False

        company = companies['companies'][0]
        company_id = company['id']
        company_name = company['name']

        print(f"\nTesting with company: {company_name} (ID: {company_id})")

        # Test officers for this company
        response = requests.get(f"{BACKEND_URL}/api/officers/company/{company_id}")
        response.raise_for_status()
        officers = response.json()
        print(f"✓ Found {len(officers)} officers for {company_name}")

        # Test bonds for this company
        response = requests.get(f"{BACKEND_URL}/api/convertible-bonds/company/{company_id}")
        response.raise_for_status()
        bonds = response.json()
        print(f"✓ Found {len(bonds)} bonds for {company_name}")

        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Frontend-Backend Integration Test")
    print("=" * 60)

    results = []

    results.append(("Officers API", test_officers_api()))
    results.append(("Convertible Bonds API", test_convertible_bonds_api()))
    results.append(("CB Subscribers API", test_cb_subscribers_api()))
    results.append(("Company-Specific Data", test_company_specific_data()))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n✓ All tests passed! Frontend can now access backend APIs.")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")

    return all_passed


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
