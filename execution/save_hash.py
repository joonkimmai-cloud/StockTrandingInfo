import bcrypt

password = "dhei@d)(djw$(diow!)"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

with open('admin_hash.txt', 'w') as f:
    f.write(hashed)
