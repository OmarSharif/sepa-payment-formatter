# ── BANK-SPECIFIC RULES ──────────────────────────────────────────────────
# Source: Individual bank implementation guides and EPC SCT rulebook 2025
# Three rules per bank:
#   Rule 1: Payment method — missing is fixable, wrong value Claude decides
#   Rule 2: IBAN country mismatch — flag for human
#   Rule 3: Amount decimal format — fixable by agent

BANK_RULES = {
    "DEUTDEDB": {
        "name": "Deutsche Bank",
        "home_country": "DE",
        "sepa_currency": "EUR",
        "source": "Deutsche Bank flow briefing — New SEPA Rulebook 2024"
    },
    "DEUTDEFF": {
        "name": "Deutsche Bank Frankfurt",
        "home_country": "DE",
        "sepa_currency": "EUR",
        "source": "Deutsche Bank flow briefing — New SEPA Rulebook 2024"
    },
    "BNPAFRPP": {
        "name": "BNP Paribas",
        "home_country": "FR",
        "sepa_currency": "EUR",
        "source": "EPC SCT Implementation Guidelines — SEPA member bank"
    },
    "ABNANL2A": {
        "name": "ABN AMRO",
        "home_country": "NL",
        "sepa_currency": "EUR",
        "source": "ABN AMRO SEPA Implementation Guidelines — March 2024"
    },
    "COBADEFF": {
        "name": "Commerzbank",
        "home_country": "DE",
        "sepa_currency": "EUR",
        "source": "EPC SCT Implementation Guidelines — SEPA member bank"
    }
}


def validate_bank_rules(payment: dict) -> dict:
    """
    Validates a payment against bank-specific rules.

    Rule 1: Payment method must be TRF for SEPA
            → missing: agent fixes to TRF (clear default)
            → wrong value: Claude decides if typo or different payment type

    Rule 2: Receiver IBAN country should match bank home country
            → flag for human, agent cannot decide if cross-border is intended

    Rule 3: Amount must have exactly 2 decimal places
            → fixable by agent

    Returns a dict with:
        - is_valid: bool
        - bank: recognized bank name or "Unknown"
        - errors: list of rule violations with fix instructions
        - warnings: list of non-blocking issues for human review
    """
    errors = []
    warnings = []
    bank_name = "Unknown"

    receiver_bic = payment.get("receiver_bic", "")
    bic_key = receiver_bic[:8] if len(receiver_bic) >= 8 else receiver_bic
    receiver_iban = payment.get("receiver_iban", "")
    payment_method = payment.get("payment_method", "")
    amount = payment.get("amount", None)

    if bic_key not in BANK_RULES:
        warnings.append(
            f"BIC {receiver_bic} not in bank rules library — "
            f"no bank-specific rules applied"
        )
        return {
            "is_valid": True,
            "bank": "Unknown",
            "errors": errors,
            "warnings": warnings
        }

    bank = BANK_RULES[bic_key]
    bank_name = bank["name"]

    # ── Rule 1: Payment method ────────────────────────────────────────────
    if not payment_method:
        # missing entirely — agent can safely default to TRF
        errors.append({
            "rule": "payment_method",
            "message": f"{bank_name}: payment method is missing. "
                       f"SEPA Credit Transfers require TRF.",
            "fixable": True,
            "fix": "TRF",
            "source": bank["source"]
        })
    elif payment_method != "TRF":
        # wrong value — Claude decides whether this is a typo or
        # a different payment type entirely (cheque, direct debit, etc.)
        errors.append({
            "rule": "payment_method",
            "message": f"{bank_name}: payment method '{payment_method}' "
                       f"is not valid for SEPA Credit Transfer. "
                       f"Required: TRF. Determine if this is a formatting "
                       f"issue or a fundamentally different payment type.",
            "fixable": "claude_decides",
            "fix": None,
            "source": bank["source"]
        })

    # ── Rule 2: IBAN country vs bank home country ─────────────────────────
    if receiver_iban and len(receiver_iban) >= 2:
        iban_country = receiver_iban[:2].upper()
        if iban_country != bank["home_country"]:
            warnings.append({
                "rule": "iban_country_mismatch",
                "message": f"{bank_name} is based in {bank['home_country']} "
                           f"but receiver IBAN is from {iban_country}. "
                           f"Cross-border routing will apply — "
                           f"verify this is intentional.",
                "fixable": False,
                "source": bank["source"]
            })

    # ── Rule 3: Amount decimal format ─────────────────────────────────────
    if amount is not None:
        amount_str = str(float(amount))
        if "." in amount_str:
            decimal_places = len(amount_str.split(".")[1])
            if decimal_places != 2:
                fixed_amount = f"{float(amount):.2f}"
                errors.append({
                    "rule": "amount_decimals",
                    "message": f"{bank_name}: amount {amount} has "
                               f"{decimal_places} decimal place(s). "
                               f"SEPA requires exactly 2 decimal places.",
                    "fixable": True,
                    "fix": fixed_amount,
                    "source": bank["source"]
                })

    return {
        "is_valid": len(errors) == 0,
        "bank": bank_name,
        "errors": errors,
        "warnings": warnings
    }


if __name__ == "__main__":
    # test case hitting all three rules
    test_payment = {
        "payment_id": "PAY-TEST-001",
        "amount": 1500.5,                        # Rule 3: wrong decimals — fixable
        "currency": "EUR",
        "payment_method": "cheque",              # Rule 1: wrong — Claude decides
        "receiver_iban": "FR7630006000011234567890189",  # Rule 2: FR to DE — warn
        "receiver_bic": "DEUTDEDB"
    }

    result = validate_bank_rules(test_payment)

    print(f"Bank:  {result['bank']}")
    print(f"Valid: {result['is_valid']}")

    if result["errors"]:
        print(f"\nErrors ({len(result['errors'])}):")
        for e in result["errors"]:
            fixable = e["fixable"]
            if fixable is True:
                label = "✓ agent fixes"
            elif fixable == "claude_decides":
                label = "? claude decides"
            else:
                label = "✗ needs human"
            fix_info = f" → fix to: {e['fix']}" if e["fix"] else ""
            print(f"  [{label}] {e['rule']}: {e['message']}{fix_info}")

    if result["warnings"]:
        print(f"\nWarnings ({len(result['warnings'])}):")
        for w in result["warnings"]:
            print(f"  ⚠ {w['rule']}: {w['message']}")