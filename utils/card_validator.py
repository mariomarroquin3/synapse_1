def is_luhn_valid(card_number: str) -> bool:
    """
    Checks if a card number is valid using the Luhn Algorithm.
    """
    if not card_number.isdigit():
        return False

    digits = [int(d) for d in card_number]
    # 1. Remove the last digit (check digit)
    check_digit = digits.pop()
    
    # 2. Reverse the remaining digits
    digits.reverse()
    
    # 3. Double the digits in odd positions (index 0, 2, 4...)
    for i in range(len(digits)):
        if i % 2 == 0:
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
                
    # 4. Sum everything and add the check digit
    total_sum = sum(digits) + check_digit
    
    # 5. If total % 10 == 0, it's valid
    return total_sum % 10 == 0