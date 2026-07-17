from app.services.auth_service import hash_password, verify_password

h = hash_password("test123")
print("Hash genere:", h)
print("Le bon mot de passe est reconnu:", verify_password("test123", h))
print("Un mauvais mot de passe est rejete:", not verify_password("wrong", h))
