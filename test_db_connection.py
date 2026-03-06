"""
Test database connection to diagnose connection issues.
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

async def test_connection():
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not set in environment!")
        return
    
    print(f"Testing connection to: {database_url[:50]}...")
    print()
    
    # Parse the URL
    if "postgresql://" in database_url:
        # Extract connection details
        url = database_url.replace("postgresql://", "").replace("postgresql+asyncpg://", "")
        if "@" in url:
            auth, rest = url.split("@", 1)
            if ":" in auth:
                user, password = auth.split(":", 1)
            else:
                user = auth
                password = ""
            
            if "/" in rest:
                host_port, database = rest.split("/", 1)
                if "?" in database:
                    database = database.split("?")[0]
            else:
                host_port = rest
                database = ""
            
            if ":" in host_port:
                host, port = host_port.split(":", 1)
            else:
                host = host_port
                port = "5432"
            
            print(f"Connection details:")
            print(f"  Host: {host}")
            print(f"  Port: {port}")
            print(f"  User: {user}")
            print(f"  Database: {database}")
            print(f"  Password: {'*' * len(password) if password else 'NOT SET'}")
            print()
    
    try:
        # Try to connect
        print("Attempting connection...")
        
        # Convert postgresql:// to postgresql+asyncpg:// if needed
        if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Remove query parameters for asyncpg
        if "?" in database_url:
            database_url = database_url.split("?")[0]
        
        # Parse for asyncpg.connect
        url_parts = database_url.replace("postgresql+asyncpg://", "").replace("postgresql://", "")
        if "@" in url_parts:
            auth, rest = url_parts.split("@", 1)
            user, password = auth.split(":", 1) if ":" in auth else (auth, "")
            host_port, database = rest.split("/", 1) if "/" in rest else (rest, "")
            host, port = host_port.split(":", 1) if ":" in host_port else (host_port, "5432")
            
            if "?" in database:
                database = database.split("?")[0]
        else:
            print("❌ Could not parse DATABASE_URL")
            return
        
        print(f"Connecting to {host}:{port}...")
        conn = await asyncpg.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            ssl='require'  # Try with SSL first
        )
        
        print("✅ Successfully connected to database!")
        
        # Test a simple query
        result = await conn.fetchval("SELECT version()")
        print(f"✅ Database version: {result[:50]}...")
        
        await conn.close()
        print("✅ Connection closed successfully")
        
    except asyncpg.exceptions.InvalidPasswordError:
        print("❌ Invalid password!")
        print("   Check your DATABASE_URL password")
    except asyncpg.exceptions.InvalidCatalogNameError:
        print("❌ Database does not exist!")
        print(f"   Database name: {database}")
        print("   Check if the database exists or create it")
    except ConnectionRefusedError:
        print("❌ Connection refused!")
        print("   Check:")
        print("   1. Database server is running")
        print("   2. Host and port are correct")
        print("   3. Firewall allows connections")
    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}")
        print(f"   Error: {e}")
        print()
        print("Troubleshooting:")
        print("1. Verify DATABASE_URL is correct")
        print("2. Check database server is accessible")
        print("3. Verify credentials are correct")
        print("4. Check SSL requirements")
        print("5. For cloud databases (Render, Neon, etc.), ensure:")
        print("   - Connection string uses correct format")
        print("   - SSL is enabled")
        print("   - IP whitelist allows your IP (if required)")

if __name__ == "__main__":
    asyncio.run(test_connection())
