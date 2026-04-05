import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()


def fix_xml(xml_string: str, schema_errors: list, bank_rule_errors: list) -> dict:
    """
    Uses Claude to fix a pain.001 XML string based on schema and bank rule errors.
    
    Claude fixes:
        - Deterministic errors automatically (amount decimals, missing payment method)
        - Ambiguous errors using reasoning (wrong payment method value)
        - Flags errors it cannot fix safely (missing required fields, wrong currency)

    Returns a dict with:
        - fixed_xml: the corrected XML string (or original if unfixable)
        - fixes_applied: list of what Claude changed
        - could_not_fix: list of errors Claude could not safely resolve
        - requires_human: list of issues needing human review
    """

    # build a combined error summary for Claude
    all_errors = []

    for error in schema_errors:
        all_errors.append(f"SCHEMA ERROR: {error}")

    for error in bank_rule_errors:
        fixable = error.get("fixable")
        if fixable is True:
            all_errors.append(
                f"BANK RULE ERROR (auto-fixable): {error['message']} "
                f"→ suggested fix: {error['fix']}"
            )
        elif fixable == "claude_decides":
            all_errors.append(
                f"BANK RULE ERROR (judgment required): {error['message']}"
            )
        else:
            all_errors.append(
                f"BANK RULE ERROR (needs human): {error['message']}"
            )

    errors_summary = "\n".join(all_errors) if all_errors else "No errors found."

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system="""You are a SEPA payment XML specialist. You will be given a 
pain.001.001.09 XML file and a list of validation errors.

Your job is to fix the XML where you can do so safely and return a JSON response.

Rules for fixing:
- Fix amount decimal errors: always round to exactly 2 decimal places
- Fix missing payment method: set to TRF
- For wrong payment method values: reason about whether it looks like a typo 
  (e.g. 'trf', 'TRFx') → fix to TRF, or a different payment type 
  (e.g. 'cheque', 'direct debit', 'DD') → do not fix, flag for human
- Do not fix missing required fields like currency or creditor name — 
  you cannot guess these safely
- Do not change amounts, IBANs, names, or dates unless explicitly told to

Respond ONLY in this exact JSON format:
{
    "fixed_xml": "the complete corrected XML string",
    "fixes_applied": ["list of what you changed and why"],
    "could_not_fix": ["list of errors you could not safely resolve"],
    "requires_human": ["list of issues needing human review or judgment"]
}""",
        messages=[
            {
                "role": "user",
                "content": f"""Please fix this pain.001 XML based on the following errors:

ERRORS:
{errors_summary}

XML TO FIX:
{xml_string}"""
            },
            {
                "role": "assistant",
                "content": "{"
            }
        ]
    )

    response_text = "{" + message.content[0].text

    try:
        result = json.loads(response_text)
        return result
    except json.JSONDecodeError:
        return {
            "fixed_xml": xml_string,
            "fixes_applied": [],
            "could_not_fix": ["Failed to parse Claude response"],
            "requires_human": ["Manual review required"]
        }


if __name__ == "__main__":
    # test XML with two fixable issues:
    # 1. amount has wrong decimals (1500.5 instead of 1500.50)
    # 2. payment method is missing
    test_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
    <CstmrCdtTrfInitn>
        <GrpHdr>
            <MsgId>TEST-001</MsgId>
            <CreDtTm>2026-04-01T10:00:00</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>1500.5</CtrlSum>
            <InitgPty>
                <Nm>Test Corporation</Nm>
            </InitgPty>
        </GrpHdr>
        <PmtInf>
            <PmtInfId>PMTINF-001</PmtInfId>
            <PmtMtd>cheque</PmtMtd>
            <ReqdExctnDt>
                <Dt>2026-04-02</Dt>
            </ReqdExctnDt>
            <Dbtr>
                <Nm>Test Corporation</Nm>
            </Dbtr>
            <DbtrAcct>
                <Id>
                    <IBAN>DE89370400440532013000</IBAN>
                </Id>
            </DbtrAcct>
            <DbtrAgt>
                <FinInstnId>
                    <BICFI>DEUTDEDB</BICFI>
                </FinInstnId>
            </DbtrAgt>
            <CdtTrfTxInf>
                <PmtId>
                    <EndToEndId>E2E-001</EndToEndId>
                </PmtId>
                <Amt>
                    <InstdAmt Ccy="EUR">1500.5</InstdAmt>
                </Amt>
                <CdtrAgt>
                    <FinInstnId>
                        <BICFI>BNPAFRPP</BICFI>
                    </FinInstnId>
                </CdtrAgt>
                <Cdtr>
                    <Nm>Supplier GmbH</Nm>
                </Cdtr>
                <CdtrAcct>
                    <Id>
                        <IBAN>FR7630006000011234567890189</IBAN>
                    </Id>
                </CdtrAcct>
            </CdtTrfTxInf>
        </PmtInf>
    </CstmrCdtTrfInitn>
</Document>"""

    # simulate errors from bank rules validator
    test_bank_errors = [
        {
            "rule": "amount_decimals",
            "message": "Deutsche Bank: amount 1500.5 has 1 decimal place(s). SEPA requires exactly 2 decimal places.",
            "fixable": True,
            "fix": "1500.50"
        },
        {
            "rule": "payment_method",
            "message": "Deutsche Bank: payment method 'cheque' is not valid for SEPA Credit Transfer. Required: TRF. Determine if this is a formatting issue or a fundamentally different payment type.",
            "fixable": "claude_decides",
            "fix": None
        }
    ]

    print("Running XML fixer...\n")
    result = fix_xml(test_xml, [], test_bank_errors)

    print("Fixes applied:")
    for fix in result.get("fixes_applied", []):
        print(f"  ✓ {fix}")

    print("\nCould not fix:")
    for item in result.get("could_not_fix", []):
        print(f"  ✗ {item}")

    print("\nRequires human:")
    for item in result.get("requires_human", []):
        print(f"  ⚠ {item}")

    print("\nFixed XML preview (first 500 chars):")
    print(result.get("fixed_xml", "")[:500])