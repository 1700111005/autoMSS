from server.utils import ListResponse
from server.datebase.knowledge import list_kbs_from_db


async def list_kbs():
    # Get List of Knowledge Base
    return ListResponse(data=list_kbs_from_db())