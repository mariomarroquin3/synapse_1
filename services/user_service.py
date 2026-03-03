from models.user_model import create_user, get_user_by_id
from utils.security import hash_password

# Constants to avoid typos
ROLE_CAJERO = 1
ROLE_CLIENTE = 2
ROLE_ADMIN = 3
ROLE_ANALISTA = 4
ROLE_AUDITOR = 5

def register_user_with_permissions(creator_id, user_data):
    """
    Business Rule: Only Admin (3) can create staff roles (1, 3, 4, 5).
    Public registration (no creator) can only create Clients (2).
    
    Args:
        creator_id (int | None): The ID of the user creating this new user.
                                 None for public registration.
        user_data (dict): Dictionary containing:
                         - role_id (int): Target role (default: 2=Cliente)
                         - email (str): User email
                         - password (str): Plain text password
                         - dui (str): DUI identifier
                         - full_name (str): Full name
                         - gender (str): M/F
                         - nit (str, optional): NIT identifier
                         - phone_number (str, optional): Phone
                         
    Returns:
        dict: {'success': bool, 'user_id': int | None, 'error': str | None}
    """
    target_role = user_data.get('role_id', ROLE_CLIENTE)
    
    # RULE: If creating staff (non-Cliente), must be an Admin
    if target_role != ROLE_CLIENTE:
        if not creator_id:
            return {"success": False, "error": "Staff creation requires an authenticated Admin."}
        
        # Get creator as a Dictionary (now guaranteed by Dictionary Wrapper)
        creator = get_user_by_id(creator_id)
        
        # Validate creator exists
        if not creator:
            return {"success": False, "error": f"Creator user ID {creator_id} not found."}
        
        # Validate creator is Admin
        if creator['role_id'] != ROLE_ADMIN:
            return {"success": False, "error": f"Permission Denied: Only Admins can create staff. User '{creator['full_name']}' has role {creator['role_id']}."}

    # If rules pass, proceed to creation
    try:
        pw_hash = hash_password(user_data['password'])
        new_id = create_user(
            role_id=target_role,
            email=user_data['email'],
            password_hash=pw_hash,
            nit=user_data.get('nit'),
            dui=user_data['dui'],
            full_name=user_data['full_name'],
            gender=user_data['gender'],
            phone_number=user_data.get('phone_number')
        )
        return {"success": True, "user_id": new_id}
    except Exception as e:
        return {"success": False, "error": str(e)}