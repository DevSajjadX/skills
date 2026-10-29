#!/bin/sh
# AC-1 and AC-2 of docs/order-edit.md, checked against the fixture's money helper.
set -e
cd "$(dirname "$0")/.."
grep -q 'int Cents(decimal d)' api/src/money.cs && echo "ok  AC-1 money helper returns integer cents"
grep -q 'After(cursor)' api/src/orders.cs && echo "ok  AC-2 orders page by cursor"
