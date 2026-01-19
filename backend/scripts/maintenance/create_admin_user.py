#!/usr/bin/env python3
"""
Create Admin User Script
"""
import psycopg2
import hashlib
import uuid

def hash_password(password: str) -> str:
    """Simple password hashing for development"""
    # In production, use proper bcrypt
    return hashlib.sha256(password.encode()).hexdigest()

# Database connection
DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_NAME = "raymontology_dev"
DB_USER = "postgres"
DB_PASSWORD = "dev_password"

def create_admin():
    print("=" * 70)
    print("👤 Creating Admin User")
    print("=" * 70)

    # Admin credentials
    admin_email = "admin@raymontology.com"
    admin_password = "admin123"  # Change this in production!
    admin_name = "System Administrator"

    # Hash password
    hashed_password = hash_password(admin_password)
    admin_id = str(uuid.uuid4())

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()

        # Check if admin already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
        existing = cursor.fetchone()

        if existing:
            print(f"⚠️  Admin user already exists: {admin_email}")
            print(f"   User ID: {existing[0]}")
        else:
            # Insert admin user
            cursor.execute("""
                INSERT INTO users (id, email, password_hash, full_name, is_active, is_superuser, subscription_plan)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (admin_id, admin_email, hashed_password, admin_name, True, True, 'enterprise'))

            conn.commit()

            print(f"✅ Admin user created successfully!")
            print(f"   Email: {admin_email}")
            print(f"   Password: {admin_password}")
            print(f"   User ID: {admin_id}")
            print(f"\n⚠️  IMPORTANT: Change the password after first login!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
        return False

    print("=" * 70)
    return True

if __name__ == "__main__":
    create_admin()
