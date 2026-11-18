# Requirements Specification — ATM Cash Withdrawal

Document: SPEC-ATM-010
Revision: B
Status: Released for interaction design
Scope: The cash-withdrawal interaction between a customer, an ATM and the
issuing bank's authorisation server, from card insertion to card return.
Excludes deposits, transfers and ATM replenishment.

---

## 1. Applicable Standards

| Reference | Title | Applies to |
|---|---|---|
| ISO 9564-1 | Financial services — PIN management and security | PIN entry, PIN block protection |
| ISO 8583 | Financial transaction card originated messages | ATM-to-host authorisation messages |
| EMV Integrated Circuit Card Specifications | Chip card transaction processing | Card reading and cardholder verification |
| PCI PIN Security Requirements | PIN handling at acquiring institutions | PIN transmission |

---

## 2. Participants

| Participant | Role |
|---|---|
| Customer | Holds the card and PIN; requests the withdrawal |
| ATMMachine | Reads the card, captures the PIN, dispenses cash, prints the receipt |
| BankServer | Authenticates the PIN and authorises the withdrawal against the account |

---

## 3. Functional Requirements

**REQ-001 — Card reading**
The ATM shall read the card number, expiry date and issuer identification from
the inserted card.
- The ATM shall reject an expired card before PIN entry.
*Verification:* Test — valid, expired and unreadable cards.

**REQ-002 — PIN entry**
The ATM shall prompt for the PIN after the card has been read and shall mask
every digit on the display.
- The PIN shall be encrypted into an ISO 9564 PIN block inside the encrypting PIN
  pad and never held in plaintext outside it.
*Verification:* Inspection — PIN pad certification; test — display masking.

**REQ-003 — PIN authentication**
The ATM shall send the card data and encrypted PIN block to the BankServer and
proceed only on receipt of an authentication token.
- On a failed authentication the ATM shall allow up to two further attempts.
- After three failed attempts the ATM shall retain the card.
*Verification:* Test — correct PIN; one, two and three incorrect attempts.

**REQ-004 — Amount entry**
After successful authentication the ATM shall display the available balance and
accept a withdrawal amount.
- The amount shall be a positive multiple of the smallest note denomination
  loaded in the dispenser.
*Verification:* Test — valid amount and amounts not divisible by the smallest note.

**REQ-005 — Withdrawal authorisation**
The BankServer shall authorise the withdrawal only if the available balance and
the daily withdrawal limit both cover the amount, and shall return the result.
- On authorisation, the BankServer shall debit the account by the amount.
- On refusal, the ATM shall display the reason and dispense nothing.
*Verification:* Test — sufficient funds, insufficient funds, limit exceeded.

**REQ-006 — Cash dispensing**
The ATM shall dispense notes totalling the authorised amount and present them to
the customer.
- If notes are not taken within 30 s the ATM shall retract them and notify the
  BankServer to reverse the debit.
*Verification:* Test — dispense and take; dispense and leave.

**REQ-007 — Receipt**
The ATM shall print a receipt showing the amount, date and time, a masked card
number and the transaction reference.
*Verification:* Inspection — printed receipt content.

**REQ-008 — Card return**
The ATM shall return the card to the customer at the end of the transaction.
- If the card is not taken within 30 s the ATM shall retain it.
*Verification:* Test — card taken; card left.

---

## 4. Non-Functional Requirements

**REQ-NF-001 — Authorisation response**
The BankServer shall respond to an authorisation request within 5 s.
*Verification:* Test — response time over 1,000 transactions.

**REQ-NF-002 — Session timeout**
The ATM shall end the session and return the card if the customer makes no input
for 60 s.
*Verification:* Test — idle at each prompt.

---

## 5. Constraints

| ID | Constraint | Value | Traces to |
|---|---|---|---|
| C1 | Maximum PIN attempts before card retention | 3 | REQ-003 |
| C2 | Cash presentation timeout | 30 s | REQ-006 |
| C3 | Card presentation timeout | 30 s | REQ-008 |
| C4 | Idle session timeout | 60 s | REQ-NF-002 |
| C5 | Host message format | ISO 8583 | REQ-003, REQ-005 |

---

## 6. Open Points

- The requested flow returns the card last, after cash and receipt. Common
  industry practice presents the card before the cash, to reduce cards left in
  the machine. The final sequence is to be confirmed.
