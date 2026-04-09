import anthropic
import json
import os
from dotenv import load_dotenv
from tools.schema_validator import validate_schema
from tools.iban_validator import validate_iban
from tools.bank_rules import validate_bank_rules
from tools.xml_fixer import fix_xml

load_dotenv()

client = anthropic.Anthropic()

# ── TOOL DEFINITIONS ─────────────────────────────────────────────────────
tools = [
    {
        "name": "validate_schema",
        "description": """Validates a pain.001.001.09 XML string against the
official ISO 20022 EPC schema. Use this first before any other validation.
Returns whether the XML is structurally valid and lists any schema errors.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "xml_string": {
                    "type": "string",
                    "description": "The pain.001.001.09 XML string to validate"
                }
            },
            "required": ["xml_string"]
        }
    },
    {
        "name": "validate_iban",
        "description": """Validates an IBAN number using the ibanapi.com REST API.
Returns whether the IBAN is valid, the bank name, BIC code, and whether
the country is a SEPA member. Call this for both sender and receiver IBANs.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "iban": {
                    "type": "string",
                    "description": "The IBAN to validate"
                }
            },
            "required": ["iban"]
        }
    },
    {
        "name": "validate_bank_rules",
        "description": """Validates a payment dictionary against bank-specific
business rules for known SEPA banks. Checks payment method, IBAN country
matching, and amount decimal format. Call this after schema validation.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "payment": {
                    "type": "object",
                    "description": "Payment data with fields: receiver_bic, receiver_iban, payment_method, amount, currency"
                }
            },
            "required": ["payment"]
        }
    },
    {
        "name": "fix_xml",
        "description": """Attempts to fix a pain.001 XML string based on schema
errors and bank rule errors. Fixes deterministic errors automatically, uses
judgment for ambiguous errors, and flags issues requiring human review.
Only call this if there are errors to fix.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "xml_string": {
                    "type": "string",
                    "description": "The XML string to fix"
                },
                "schema_errors": {
                    "type": "array",
                    "description": "List of schema error strings from validate_schema",
                    "items": {"type": "string"}
                },
                "bank_rule_errors": {
                    "type": "array",
                    "description": "List of bank rule error objects from validate_bank_rules",
                    "items": {"type": "object"}
                }
            },
            "required": ["xml_string", "schema_errors", "bank_rule_errors"]
        }
    }
]


def run_tool(tool_name: str, tool_input: dict) -> str:
    """Routes tool calls from Claude to the correct Python function."""
    if tool_name == "validate_schema":
        result = validate_schema(tool_input["xml_string"])
    elif tool_name == "validate_iban":
        result = validate_iban(tool_input["iban"])
    elif tool_name == "validate_bank_rules":
        result = validate_bank_rules(tool_input["payment"])
    elif tool_name == "fix_xml":
        result = fix_xml(
            tool_input["xml_string"],
            tool_input.get("schema_errors", []),
            tool_input.get("bank_rule_errors", [])
        )
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result)


def run_agent(payment_xml: str, payment_data: dict) -> dict:
    """
    Runs the full SEPA payment validation agent.

    The agent:
    1. Validates XML structure against the EPC schema
    2. Validates sender and receiver IBANs via live API
    3. Validates bank-specific business rules
    4. Fixes errors where possible
    5. Revalidates the fixed XML
    6. Returns a complete validation report
    """
    print("\n" + "="*60)
    print("SEPA PAYMENT VALIDATION AGENT")
    print("="*60)

    messages = [
        {
            "role": "user",
            "content": f"""You are validating a SEPA payment file.
Please perform a complete validation using the available tools in this order:

1. Validate the XML schema using validate_schema
2. Validate both IBANs using validate_iban
3. Validate bank-specific rules using validate_bank_rules
4. If there are any errors, attempt to fix them using fix_xml
5. If you fixed the XML, revalidate the schema to confirm the fixes worked

Payment data for bank rules validation:
{json.dumps(payment_data, indent=2)}

XML to validate:
{payment_xml}

After completing all validations provide a final summary report."""
        }
    ]

    # ── AGENT LOOP ───────────────────────────────────────────────────────
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        # add Claude's response to conversation history
        messages.append({
            "role": "assistant",
            "content": response.content
        })

        # check if Claude is done
        if response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text = block.text
            print("\nAGENT REPORT:")
            print(final_text)
            return {"status": "complete", "report": final_text}

        # process tool calls
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    print(f"\n→ Calling tool: {block.name}")
                    preview = json.dumps(block.input)[:100]
                    print(f"  Input: {preview}...")

                    result = run_tool(block.name, block.input)
                    result_preview = result[:200]
                    print(f"  Result: {result_preview}...")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # send tool results back to Claude
            messages.append({
                "role": "user",
                "content": tool_results
            })


if __name__ == "__main__":
    test_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
    <CstmrCdtTrfInitn>
        <GrpHdr>
            <MsgId>PAY-2026-001</MsgId>
            <CreDtTm>2026-04-01T10:00:00</CreDtTm>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>2500.5</CtrlSum>
            <InitgPty>
                <Nm>Acme Corporation</Nm>
            </InitgPty>
        </GrpHdr>
        <PmtInf>
            <PmtInfId>PMTINF-001</PmtInfId>
            <PmtMtd>TRF</PmtMtd>
            <NbOfTxs>1</NbOfTxs>
            <CtrlSum>2500.5</CtrlSum>
            <PmtTpInf>
                <SvcLvl>
                    <Cd>SEPA</Cd>
                </SvcLvl>
            </PmtTpInf>
            <ReqdExctnDt>
                <Dt>2026-04-02</Dt>
            </ReqdExctnDt>
            <Dbtr>
                <Nm>Acme Corporation</Nm>
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
                    <InstdAmt Ccy="EUR">2500.5</InstdAmt>
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

    test_payment_data = {
        "payment_id": "PAY-2026-001",
        "amount": 2500.5,
        "currency": "EUR",
        "payment_method": "TRF",
        "sender_iban": "DE89370400440532013000",
        "receiver_iban": "FR7630006000011234567890189",
        "receiver_bic": "BNPAFRPP"
    }

    run_agent(test_xml, test_payment_data)