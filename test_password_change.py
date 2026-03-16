#!/usr/bin/env python3
"""
Test script for complete password change workflow.
Tests: validate_password(), change_password(), and update_user_password()
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from utils.security import validate_password, hash_password, verify_password
from services.auth_service import change_password, login
from models.user_model import create_user, get_user_by_id, update_user_password
from config.database import get_cursor


def test_validate_password():
    """Test password validation function"""
    print("\n" + "="*60)
    print("TEST 1: Password Validation Function")
    print("="*60)
    
    test_cases = [
        ("weak", False),  # Too short
        ("Weak1", False),  # Too short
        ("WeakPassword", False),  # No digit
        ("Weak1Pass", False),  # No special char
        ("Weak1Pass!", True),  # Valid
        ("Strong@Password123", True),  # Valid
        ("Test@123", True),  # Valid
    ]
    
    for password, expected_valid in test_cases:
        is_valid, missing = validate_password(password)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"{status} '{password}': valid={is_valid}, missing={missing}")
        

def test_update_user_password():
    """Test update_user_password function"""
    print("\n" + "="*60)
    print("TEST 2: Update User Password Function")
    print("="*60)
    
    # Create test user
    test_user_data = {
        'email': f'testpass_update_@test.com',
        'password': 'InitialPass@123',
        'full_name': 'Test User',
        'gender': 'M',
        'phone_number': '50312345678',
        'DUI': '12345678-9'
    }
    
    user_id = create_user(
        role_id=2,  # Regular user
        email=test_user_data['email'],
        password_hash=hash_password(test_user_data['password']),
        nit=None,
        dui=test_user_data['DUI'],
        full_name=test_user_data['full_name'],
        gender=test_user_data['gender'],
        phone_number=test_user_data['phone_number']
    )
    
    print(f"✅ Created test user: {user_id}")
    
    # Test update_user_password
    new_password = "UpdatedPass@456"
    new_hash = hash_password(new_password)
    result = update_user_password(user_id, new_hash)
    
    if result:
        print(f"✅ Password updated for user {user_id}")
        
        # Verify the new password works
        user_updated = get_user_by_id(user_id)
        if verify_password(new_password, user_updated['password_hash']):
            print(f"✅ New password verified successfully")
        else:
            print(f"❌ New password verification failed")
    else:
        print(f"❌ Failed to update password")


def test_change_password_full_flow():
    """Test complete change_password flow"""
    print("\n" + "="*60)
    print("TEST 3: Complete Change Password Flow")
    print("="*60)
    
    # Create test user
    test_user_data = {
        'email': f'testcpass_flow@test.com',
        'password': 'OriginalPass@123',
        'full_name': 'Test Flow User',
        'gender': 'F',
        'phone_number': '50312345679',
        'DUI': '87654321-0'
    }
    
    user_id = create_user(
        role_id=2,
        email=test_user_data['email'],
        password_hash=hash_password(test_user_data['password']),
        nit=None,
        dui=test_user_data['DUI'],
        full_name=test_user_data['full_name'],
        gender=test_user_data['gender'],
        phone_number=test_user_data['phone_number']
    )
    
    print(f"✅ Created test user: {user_id}")
    
    # Step 1: Test with wrong current password
    print("\n📋 Step 1: Try with wrong current password...")
    success, message = change_password(user_id, "WrongPass@123", "NewPass@456")
    if not success and "incorrecta" in message.lower():
        print(f"✅ Correctly rejected wrong password: {message}")
    else:
        print(f"❌ Should have rejected wrong password: {message}")
    
    # Step 2: Test with invalid new password
    print("\n📋 Step 2: Try with invalid new password (too weak)...")
    success, message = change_password(user_id, "OriginalPass@123", "weak")
    if not success and "requisitos" in message.lower():
        print(f"✅ Correctly rejected weak password: {message}")
    else:
        print(f"❌ Should have rejected weak password: {message}")
    
    # Step 3: Test with same password
    print("\n📋 Step 3: Try with same password as current...")
    success, message = change_password(user_id, "OriginalPass@123", "OriginalPass@123")
    if not success and "diferente" in message.lower():
        print(f"✅ Correctly rejected same password: {message}")
    else:
        print(f"❌ Should have rejected same password: {message}")
    
    # Step 4: Test successful password change
    print("\n📋 Step 4: Change password successfully...")
    new_password = "ValidNewPass@789"
    success, message = change_password(user_id, "OriginalPass@123", new_password)
    if success:
        print(f"✅ Password changed successfully: {message}")
        
        # Verify can login with new password
        print("\n📋 Step 5: Verify login with new password...")
        login_success, login_result = login(test_user_data['email'], new_password)
        if login_success:
            print(f"✅ Login successful with new password")
        else:
            print(f"❌ Login failed with new password: {login_result}")
            
        # Verify cannot login with old password
        print("\n📋 Step 6: Verify cannot login with old password...")
        login_fail, login_result = login(test_user_data['email'], "OriginalPass@123")
        if not login_fail:
            print(f"✅ Correctly rejected old password")
        else:
            print(f"❌ Should have rejected old password")
    else:
        print(f"❌ Password change failed: {message}")


def test_backward_compatibility():
    """Test that login doesn't enforce password validation (backward compatibility)"""
    print("\n" + "="*60)
    print("TEST 4: Login Backward Compatibility (No Validation)")
    print("="*60)
    
    # Create test user with password that would fail validation
    # This simulates a legacy password
    test_user_data = {
        'email': f'testlegacy@test.com',
        'password': 'weak',  # Weak password (legacy)
        'full_name': 'Legacy User',
        'gender': 'M',
        'phone_number': '50312345670',
        'DUI': '11111111-1'
    }
    
    user_id = create_user(
        role_id=2,
        email=test_user_data['email'],
        password_hash=hash_password(test_user_data['password']),
        nit=None,
        dui=test_user_data['DUI'],
        full_name=test_user_data['full_name'],
        gender=test_user_data['gender'],
        phone_number=test_user_data['phone_number']
    )
    
    print(f"✅ Created legacy test user with weak password")
    
    # Test login with weak password
    print("\n📋 Attempting login with weak legacy password...")
    success, result = login(test_user_data['email'], test_user_data['password'])
    if success:
        print(f"✅ Login accepted weak password (backward compatible)")
    else:
        print(f"❌ Login rejected weak password: {result}")


if __name__ == "__main__":
    print("\n" + "🔐 PASSWORD SECURITY SYSTEM - COMPREHENSIVE TEST SUITE 🔐".center(70))
    
    try:
        test_validate_password()
        test_update_user_password()
        test_change_password_full_flow()
        test_backward_compatibility()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
