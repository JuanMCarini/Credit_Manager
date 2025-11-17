# database/structure/client/__init__.py

from str.database.structure.clients.employers import Employer, get_employer_id
from str.database.structure.clients.main import Client
from str.database.structure.clients.search import search_id as search_client_id
from str.database.structure.clients.tool import validate_cuil

__all__ = ["Client", "Employer", "search_client_id", "validate_cuil", "get_employer_id"]
