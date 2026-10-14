from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.database import Base


def alembic_config(url: str | None = None) -> Config:
    cfg = Config("alembic.ini")
    cfg.attributes["configure_logger"] = False
    if url:
        cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_hay_una_sola_cabeza_de_migraciones():
    assert len(ScriptDirectory.from_config(alembic_config()).get_heads()) == 1


def test_las_migraciones_crean_lo_mismo_que_los_modelos(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migraciones.db').as_posix()}"
    command.upgrade(alembic_config(url), "head")
    engine = create_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    engine.dispose()
    assert diff == [], f"Hay cambios en los modelos sin migración: {diff}"


def test_las_migraciones_se_pueden_deshacer(tmp_path):
    url = f"sqlite:///{(tmp_path / 'migraciones.db').as_posix()}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
