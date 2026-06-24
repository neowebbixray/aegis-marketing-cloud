"""Test factories package for Aegis Marketing Cloud.

Provides factory_boy-based factories that generate realistic test data
for all domain models. All factories use ``SQLAlchemyModelFactory``
with ``sqlalchemy_session_persistence = None`` to support async SQLAlchemy
sessions (the fixture is responsible for calling ``await db_session.flush()``).
"""
