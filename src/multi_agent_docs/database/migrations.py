from pathlib import Path

from alembic import command
from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def build_alembic_config(database_path: Path) -> Config:
    """Собрать Alembic-конфигурацию для указанного SQLite-файла."""
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.resolve()}")
    return config


def upgrade_database(database_path: Path, revision: str = "head") -> None:
    """Обновить схему базы до требуемой ревизии."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(build_alembic_config(database_path), revision)


def downgrade_database(database_path: Path, revision: str = "base") -> None:
    """Откатить схему базы до требуемой ревизии."""
    command.downgrade(build_alembic_config(database_path), revision)
