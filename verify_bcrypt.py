from passlib.context import CryptContext

try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    password = "admin123"
    hashed = pwd_context.hash(password)
    print(f"Hashed password: {hashed}")
    
    verified = pwd_context.verify(password, hashed)
    print(f"Verification result: {verified}")
    
    if verified:
        print("Bcrypt compatibility verification SUCCESSFUL")
    else:
        print("Bcrypt verification FAILED")
except Exception as e:
    print(f"Verification FAILED with error: {e}")
    import traceback
    traceback.print_exc()
