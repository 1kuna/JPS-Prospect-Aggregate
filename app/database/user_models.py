"""
User authentication models in separate database.

This file contains only user-related models that will be stored
in a separate database for security isolation.
"""

from sqlalchemy import Column, String, Integer, TIMESTAMP
from sqlalchemy.sql import func
from app.database import db

class User(db.Model):
    __bind_key__ = 'users'
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    first_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default='user', index=True)  # 'user' or 'admin'
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', first_name='{self.first_name}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }