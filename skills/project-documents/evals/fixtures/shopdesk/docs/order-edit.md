# Order edit form: acceptance criteria
- AC-1: an edited price is stored in integer cents (test: `tests/order_edit_test.sh`).
- AC-2: the order list still pages by cursor after an edit (test: `tests/order_edit_test.sh`).
- AC-3: the form shows the saved price with a currency symbol, right-aligned in RTL (no test; manual QA).
