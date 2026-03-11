"""
Database migration script to add missing columns to existing tables.
"""
from sqlalchemy import text

from app.db.session import engine


async def migrate_outreach_logs() -> None:
    """
    Add email_subject and email_body columns to outreach_logs table if they don't exist.
    """
    async with engine.begin() as conn:
        # Check if columns exist and add them if they don't
        # PostgreSQL syntax
        await conn.execute(text("""
            DO $$ 
            BEGIN
                -- Add email_subject column if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'outreach_logs' 
                    AND column_name = 'email_subject'
                ) THEN
                    ALTER TABLE outreach_logs 
                    ADD COLUMN email_subject VARCHAR(500);
                END IF;
                
                -- Add email_body column if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'outreach_logs' 
                    AND column_name = 'email_body'
                ) THEN
                    ALTER TABLE outreach_logs 
                    ADD COLUMN email_body TEXT;
                END IF;
            END $$;
        """))


async def migrate_lead_follow_ups() -> None:
    """
    Add follow_up_count and next_follow_up_date columns to leads table if they don't exist.
    """
    async with engine.begin() as conn:
        await conn.execute(text("""
            DO $$ 
            BEGIN
                -- Add follow_up_count column if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'leads' 
                    AND column_name = 'follow_up_count'
                ) THEN
                    ALTER TABLE leads 
                    ADD COLUMN follow_up_count INTEGER DEFAULT 0 NOT NULL;
                END IF;
                
                -- Add next_follow_up_date column if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'leads' 
                    AND column_name = 'next_follow_up_date'
                ) THEN
                    ALTER TABLE leads 
                    ADD COLUMN next_follow_up_date TIMESTAMP WITH TIME ZONE;
                    CREATE INDEX IF NOT EXISTS idx_leads_next_follow_up_date ON leads(next_follow_up_date);
                END IF;
            END $$;
        """))


async def migrate_outreach_logs_event_type() -> None:
    """
    Increase the size of event_type column in outreach_logs to support FOLLOW_UP (9 chars).
    The column might be VARCHAR(7) which is too small for 'follow_up'.
    """
    async with engine.begin() as conn:
        await conn.execute(text("""
            DO $$ 
            BEGIN
                -- Check if column exists and if it's too small
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'outreach_logs' 
                    AND column_name = 'event_type'
                    AND (character_maximum_length IS NULL OR character_maximum_length < 20)
                ) THEN
                    -- Alter the column to allow longer values (VARCHAR(20) is safe)
                    ALTER TABLE outreach_logs 
                    ALTER COLUMN event_type TYPE VARCHAR(20);
                END IF;
            END $$;
        """))


async def migrate_outreach_logs_message_id() -> None:
    """
    Add message_id column to outreach_logs table for email reply threading.
    """
    async with engine.begin() as conn:
        await conn.execute(text("""
            DO $$ 
            BEGIN
                -- Add message_id column if it doesn't exist
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'outreach_logs' 
                    AND column_name = 'message_id'
                ) THEN
                    ALTER TABLE outreach_logs 
                    ADD COLUMN message_id VARCHAR(255);
                    CREATE INDEX IF NOT EXISTS idx_outreach_logs_message_id ON outreach_logs(message_id);
                END IF;
            END $$;
        """))


async def migrate_users_google_oauth() -> None:
    """
    Add Google OAuth columns to users table.
    """
    async with engine.begin() as conn:
        await conn.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'google_access_token'
                ) THEN
                    ALTER TABLE users ADD COLUMN google_access_token VARCHAR;
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'google_refresh_token'
                ) THEN
                    ALTER TABLE users ADD COLUMN google_refresh_token VARCHAR;
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'token_expiry'
                ) THEN
                    ALTER TABLE users ADD COLUMN token_expiry TIMESTAMP WITH TIME ZONE;
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'google_email'
                ) THEN
                    ALTER TABLE users ADD COLUMN google_email VARCHAR(255);
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'google_sheet_id'
                ) THEN
                    ALTER TABLE users ADD COLUMN google_sheet_id VARCHAR(255);
                END IF;
            END $$;
        """))


async def run_migrations() -> None:
    """Run all pending migrations."""
    await migrate_outreach_logs()
    await migrate_lead_follow_ups()
    await migrate_outreach_logs_event_type()
    await migrate_outreach_logs_message_id()
    await migrate_users_google_oauth()
    print("Database migrations completed successfully")

