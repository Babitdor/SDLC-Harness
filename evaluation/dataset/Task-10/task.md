Build a SysML v2 sequence diagram for a bank ATM withdrawal process.

The process flow is:
1. Customer inserts their card into the ATM
2. ATM reads the card information
3. Customer enters their PIN
4. ATM authenticates the PIN with the BankServer
5. Customer enters the withdrawal amount
6. BankServer processes the withdrawal (checks balance, approves)
7. ATM dispenses cash to the customer
8. ATM prints a receipt
9. ATM returns the card to the customer

Model this as a proper SysML v2 sequence diagram with:
- `item def` for all data types flowing between lifelines (CardData, PINEntry, AuthToken, WithdrawalRequest, TransactionResult, Cash, Receipt)
- `action def` for each step, with typed `in item` and `out item` parameters
- `part def` for the three lifelines: Customer, ATMMachine, BankServer
- A top-level `action def 'ATM Withdrawal Process'` that composes all sub-actions with proper message flows (`send` statements)
- Proper `import` of ScalarValues

Produce the complete SysML v2 sequence model.
