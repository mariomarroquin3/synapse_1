import random

def generate_luhn_card_number(prefix: str = "4", length: int = 16) -> str:
    """
    Generates a valid card number using the Luhn algorithm.
    Default prefix is '4' (Visa) and default length is 16.
    """
    # 1. Start with the prefix
    card_number = [int(x) for x in prefix]
    
    # 2. Add random digits except the last one
    while len(card_number) < length - 1:
        card_number.append(random.randint(0, 9))
    
    # 3. Calculate checksum using Luhn algorithm
    digits = card_number[::-1]
    total_sum = 0
    
    for i, digit in enumerate(digits):
        if i % 2 == 0:  # Posición impar in reverse (original original par)
            doubled = digit * 2
            if doubled > 9:
                doubled -= 9
            total_sum += doubled
        else:
            total_sum += digit
            
    # 4. Find the check digit that makes the total sum a multiple of 10
    check_digit = (10 - (total_sum % 10)) % 10
    card_number.append(check_digit)
    
    return "".join(map(str, card_number))

if __name__ == "__main__":
    # Test generation
    for _ in range(5):
        num = generate_luhn_card_number()
        print(f"Generated: {num}")
