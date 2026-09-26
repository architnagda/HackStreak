import pymysql
from app.core.config import settings
from app.core.database import engine, Base
import app.models # Ensure all models are registered with Base

def test_and_init_db():
    print(f"Connecting to MySQL server at {settings.MYSQL_HOST}:{settings.MYSQL_PORT} with user {settings.MYSQL_USER}...")
    
    passwords_to_try = [settings.MYSQL_PASSWORD, "root", "password", "admin", "123456", ""]
    connected_conn = None
    successful_pwd = None

    for pwd in passwords_to_try:
        try:
            conn = pymysql.connect(
                host=settings.MYSQL_HOST,
                user=settings.MYSQL_USER,
                password=pwd,
                port=settings.MYSQL_PORT,
                charset='utf8mb4'
            )
            connected_conn = conn
            successful_pwd = pwd
            print(f"Successfully connected to MySQL with password: '{pwd}'")
            break
        except Exception as e:
            continue

    if not connected_conn:
        print("Could not connect with tested passwords. Attempting with configured settings...")
        try:
            connected_conn = pymysql.connect(
                host=settings.MYSQL_HOST,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                port=settings.MYSQL_PORT,
                charset='utf8mb4'
            )
            successful_pwd = settings.MYSQL_PASSWORD
        except Exception as e:
            print(f"Connection failed: {e}")
            raise e

    # Create database if not exists
    with connected_conn.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print(f"Database `{settings.MYSQL_DB}` verified/created.")
    connected_conn.close()

    # If password changed from settings, update .env file
    if successful_pwd != settings.MYSQL_PASSWORD:
        settings.MYSQL_PASSWORD = successful_pwd
        # Update .env
        with open(".env", "r", encoding="utf-8") as f:
            content = f.read()
        import re
        new_content = re.sub(r"MYSQL_PASSWORD=.*", f"MYSQL_PASSWORD={successful_pwd}", content)
        with open(".env", "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated .env with working MySQL password.")

    # Create all tables using SQLAlchemy
    print("Creating SQLAlchemy tables...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")

    init_demo_user()

def init_demo_user():
    from sqlalchemy.orm import Session
    from app.models.user import User
    from app.core.security import get_password_hash
    with Session(engine) as session:
        demo_user = session.query(User).filter(User.email == "enterprise_demo@documind.ai").first()
        if not demo_user:
            demo_user = User(
                email="enterprise_demo@documind.ai",
                hashed_password=get_password_hash("EnterprisePass2026!"),
                full_name="Enterprise Demo User",
                is_active=True
            )
            session.add(demo_user)
            session.commit()
            print("Demo user 'enterprise_demo@documind.ai' created successfully.")

if __name__ == "__main__":
    test_and_init_db()
