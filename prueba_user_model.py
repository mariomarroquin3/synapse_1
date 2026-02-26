from models.user_model import create_user
from utils.security import hash_password

hashed = hash_password("124356")

create_user(
    role_id=1,
    email="test@2test.com",
    password_hash=hashed,
    nit=None,
    gender="M",
    dui="00000000-0",
    full_name="Juan Pérez",
    phone_number="7777-7547"
)