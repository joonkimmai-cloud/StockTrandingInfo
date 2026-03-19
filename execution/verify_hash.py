import bcrypt

password = "dhei@d)(djw$(diow!)"
stored_hash = "$2b$12$Yiq8mrdHAtMpWwn28UwfgOfuVv6pBI0XVwUo9629KhfA79Qx8aL2S"

# 1. Verify using bcrypt (Python)
is_valid_python = bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
print(f"[*] Python Verification: {is_valid_python}")

# 2. Re-hash to see if it matches the algorithm
new_hash = bcrypt.hashpw(password.encode('utf-8'), b'$2b$12$Yiq8mrdHAtMpWwn28UwfgOfuV').decode('utf-8')
print(f"[*] Re-hash with same salt: {new_hash}")
print(f"[*] Original Hash:          {stored_hash}")
