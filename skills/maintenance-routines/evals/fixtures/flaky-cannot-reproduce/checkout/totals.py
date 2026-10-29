def checkout_total(prices, tax_percent):
    subtotal = sum(prices)
    return subtotal + subtotal * tax_percent // 100
