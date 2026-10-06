import argparse

from .config import Settings
from .database.migrations import downgrade_database, upgrade_database


def build_parser() -> argparse.ArgumentParser:
    """Создать parser служебных команд проекта."""
    parser = argparse.ArgumentParser(description="Команды backend анализа документов")
    subparsers = parser.add_subparsers(dest="command", required=True)
    migrate = subparsers.add_parser("migrate", help="Применить миграции базы")
    migrate.add_argument("--revision", default="head")
    downgrade = subparsers.add_parser("downgrade", help="Откатить миграции базы")
    downgrade.add_argument("--revision", default="-1")
    return parser


def main() -> None:
    """Выполнить выбранную служебную команду."""
    arguments = build_parser().parse_args()
    database_path = Settings.from_env().database_path
    if arguments.command == "migrate":
        upgrade_database(database_path, arguments.revision)
    else:
        downgrade_database(database_path, arguments.revision)


if __name__ == "__main__":
    main()
