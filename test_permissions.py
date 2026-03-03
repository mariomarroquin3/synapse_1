from services.user_service import ROLE_ANALISTA, ROLE_AUDITOR, register_user_with_permissions, ROLE_ADMIN, ROLE_CAJERO, ROLE_CLIENTE

def run_tests():
    print("🧪 STARTING PERMISSION TESTS...\n")

    # SCENARIO 1: A Client (ID 5) tries to create a Cajero (ID 1)
    # Expected: FAIL
    print("Test 1: Client attempting to create a Cajero...")
    bad_request = {
        "role_id": ROLE_CAJERO,
        "email": "hackercaj@bank.com",
        "password": "123234",
        "dui": "00000002-1",
        "full_name": "Jose Juan Juárez Justo",
        "gender": "M"
    }
    res1 = register_user_with_permissions(creator_id=12, user_data=bad_request)
    print(f"Result: {'❌ Rejected (Good)' if not res1['success'] else '✅ Allowed (Wait, this is bad!)'}")
    print(f"Message: {res1.get('error')}\n")

    # SCENARIO 2: An Admin (ID 1) creates another Admin
    # Expected: SUCCESS
    print("Test 2: Admin creating a new Admin...")
    admin_request = {
        "role_id": ROLE_ADMIN,
        "email": "new2_admin@bank.com",
        "password": "secure_password",
        "dui": "99999929-9",
        "full_name": "Juana Carolina Pérez",
        "gender": "F"
    }
    res2 = register_user_with_permissions(creator_id=13, user_data=admin_request)
    print(f"Result: {'✅ Success' if res2['success'] else '❌ Failed'}")
    if not res2['success']: print(f"Error: {res2['error']}")
    print("")

    # SCENARIO 3: Public signup for a Client
    # Expected: SUCCESS
    print("Test 3: Public registration for a standard Client...")
    public_request = {
        "role_id": ROLE_CLIENTE,
        "email": "customertest2@gmail.com",
        "password": "customer_pass",
        "dui": "12341234-0",
        "full_name": "Alice Customer",
        "gender": "F"
    }
    res3 = register_user_with_permissions(creator_id=13, user_data=public_request)
    print(f"Result: {'✅ Success' if res3['success'] else '❌ Failed'}\n")


    print("Test 4: Public registration for an Analyst...")
    public_request = {
        "role_id": ROLE_ANALISTA,
        "email": "analysttest@gmail.com",
        "password": "analyst_pass",
        "dui": "12341234-1",
        "full_name": "Alice Analyst",
        "gender": "F"
    }
    res4 = register_user_with_permissions(creator_id=13, user_data=public_request)
    print(f"Result: {'✅ Success' if res4['success'] else '❌ Failed'}\n")


    print("Test 5: Public registration for an Auditor...")
    public_request = {
        "role_id": ROLE_AUDITOR,
        "email": "auditor@gmail.com",
        "password": "auditor_pass",
        "dui": "12341234-2",
        "full_name": "Alice Auditor",
        "gender": "F"
    }
    res5 = register_user_with_permissions(creator_id=13, user_data=public_request)
    print(f"Result: {'✅ Success' if res5['success'] else '❌ Failed'}\n")
if __name__ == "__main__":
    run_tests()