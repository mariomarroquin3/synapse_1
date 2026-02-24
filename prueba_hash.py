from utils.security import hash_password, verify_password

hashed = hash_password("123456")

print("Hash:", hashed)

print("Login correcto:", verify_password("123456", hashed))
print("Login incorrecto:", verify_password("111111", hashed))