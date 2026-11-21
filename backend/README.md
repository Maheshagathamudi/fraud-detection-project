# Run from the backend directory after activating its virtual environment and applying migrations.
alembic upgrade head
uvicorn app.main:app --reload
