#!/usr/bin/env python3
"""Create default users for auth."""
import uuid
import sys
sys.path.insert(0, '.')

from app.db.session import SessionLocal
from app.db.models import User
from app.core.security import get_password_hash

db = SessionLocal()
try:
    existing = db.query(User).count()
    if existing == 0:
        manager = User(
            user_id=str(uuid.uuid4()),
            username='manager_01',
            hashed_password=get_password_hash('password'),
            role='warehouse_manager',
        )
        db.add(manager)
        
        analyst = User(
            user_id=str(uuid.uuid4()),
            username='analyst_01',
            hashed_password=get_password_hash('password'),
            role='analyst',
        )
        db.add(analyst)
        
        db.commit()
        print('Created default users: manager_01 and analyst_01')
    else:
        print(f'Users already exist ({existing} users)')
except Exception as e:
    print(f'Error: {e}')
    db.rollback()
finally:
    db.close()
