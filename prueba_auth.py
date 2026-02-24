from services.auth_service import login

success, result = login("test@test.com", "123456")

print(success)
print(result)