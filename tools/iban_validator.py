import requests
import os
from dotenv import load_dotenv

load_dotenv()


def validate_iban(iban: str) -> dict:
    """
    Validates an IBAN using the ibanapi.com REST API.
    Returns validity, bank name, BIC, and SEPA membership.

    Returns a dict with:
        - is_valid: bool
        - iban: the IBAN checked
        - bank_name: name of the bank if found
        - bic: BIC code if found
        - country_code: two letter country code
        - sepa_member: whether this country is a SEPA member
        - messages: list of validation messages
    """
    clean_iban = iban.replace(" ", "").upper()
    api_key = os.getenv("IBANAPI_KEY")

    if not api_key:
        return {
            "is_valid": False,
            "iban": clean_iban,
            "bank_name": "Unknown",
            "bic": "",
            "country_code": "",
            "sepa_member": False,
            "messages": ["IBANAPI_KEY not set in .env"]
        }

    url = f"https://api.ibanapi.com/v1/validate/{clean_iban}"

    try:
        response = requests.get(
            url,
            params={"api_key": api_key},
            timeout=10
        )
        data = response.json()

        # ibanapi returns result code 200 for valid
        is_valid = data.get("result") == 200

        bank = data.get("data", {}).get("bank", {})
        sepa = data.get("data", {}).get("sepa", {})

        return {
            "is_valid": is_valid,
            "iban": clean_iban,
            "bank_name": bank.get("bank_name", "Unknown"),
            "bic": bank.get("bic", ""),
            "country_code": data.get("data", {}).get("country_code", ""),
            "sepa_member": sepa.get("sepa_credit_transfer") == "Yes",
            "messages": [data.get("message", "")]
        }

    except Exception as e:
        return {
            "is_valid": False,
            "iban": clean_iban,
            "bank_name": "Unknown",
            "bic": "",
            "country_code": "",
            "sepa_member": False,
            "messages": [f"API call failed: {str(e)}"]
        }


if __name__ == "__main__":
    # make sure requests is installed
    test_ibans = [
        "DE89370400440532013000",
        "FR7630006000011234567890189",
        "GB29NWBK60161331926819",
        "DE00000000000000000000",
    ]

    for iban in test_ibans:
        result = validate_iban(iban)
        status = "✓" if result["is_valid"] else "✗"
        print(f"{status} {iban}")
        if result["is_valid"]:
            print(f"   Bank: {result['bank_name']}")
            print(f"   BIC:  {result['bic']}")
            print(f"   SEPA: {result['sepa_member']}")
        else:
            print(f"   {result['messages'][0]}")
        print()