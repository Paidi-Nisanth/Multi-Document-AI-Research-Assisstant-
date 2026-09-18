# Import all models so Alembic can discover metadata
from app.db.base_class import Base  # noqa
from app.models.workspace import Workspace  # noqa
from app.models.user import User  # noqa
from app.models.document import Document  # noqa
from app.models.chunk import Chunk  # noqa
from app.models.embedding import Embedding  # noqa
from app.models.conversation import Conversation  # noqa
from app.models.message import Message  # noqa
from app.models.flashcard import Flashcard  # noqa
from app.models.query_cache import QueryCache  # noqa
