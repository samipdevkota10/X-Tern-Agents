#!/usr/bin/env python3
"""Add used_llm and llm_rationale columns to scenarios table."""
from app.db.session import engine
from sqlalchemy import text, inspect

def migrate():
    with engine.connect() as conn:
        # Add used_llm column
        try:
            conn.execute(text('ALTER TABLE scenarios ADD COLUMN used_llm BOOLEAN DEFAULT FALSE'))
            conn.commit()
            print('✅ Added used_llm column')
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print('used_llm already exists')
            else:
                print(f'used_llm error: {e}')
                conn.rollback()
        
        # Add llm_rationale column
        try:
            conn.execute(text('ALTER TABLE scenarios ADD COLUMN llm_rationale TEXT'))
            conn.commit()
            print('✅ Added llm_rationale column')
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print('llm_rationale already exists')
            else:
                print(f'llm_rationale error: {e}')
                conn.rollback()

    # Verify
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('scenarios')]
    print('Final columns:', columns)

if __name__ == '__main__':
    migrate()
