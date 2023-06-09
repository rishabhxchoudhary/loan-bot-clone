import re

string = "$repaid\\_confirm 12345 100 USD"
pattern = r"^\$repaid\\_confirm\s(\d{5})\s([-+]?\d*\.?\d+)\s(\w+)$"

match = re.match(pattern, string)
if match:
    id = match.group(1)
    amount = match.group(2)
    currency = match.group(3)
    print("ID:", id)
    print("Amount:", amount)
    print("Currency:", currency)
else:
    print("String does not match the pattern")
