from services.auth_service import login

success, result = login("admin", "123456")

print(success)
print(result)