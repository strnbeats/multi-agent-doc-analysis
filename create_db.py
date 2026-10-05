from src.multi_agent_docs.database.db import Base, engine
from src.multi_agent_docs.database import models


Base.metadata.create_all(bind=engine)

print("База данных создана")#это временный файл, который создаёт базу данных и таблицы в ней. После создания базы данных его можно удалить