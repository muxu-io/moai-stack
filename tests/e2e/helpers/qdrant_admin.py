"""Direct Qdrant admin for e2e: count records by type and purge a persona.

persona-store's DELETE cascades only Postgres rows; Qdrant vectors are orphaned,
so teardown purges them here. Counts back GP1/GP2 assertions. Payload keys match
persona-core's writer: 'persona_id' and 'type' (RecordType value).
"""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
)


class QdrantAdmin:
    def __init__(self, host: str, port: int, collection: str) -> None:
        self._c = QdrantClient(host=host, port=port)
        self._collection = collection

    def _filter(self, persona_id: str, record_type: str | None) -> Filter:
        must = [FieldCondition(key="persona_id", match=MatchValue(value=persona_id))]
        if record_type is not None:
            must.append(FieldCondition(key="type", match=MatchValue(value=record_type)))
        return Filter(must=must)

    def count(self, persona_id: str, record_type: str | None = None) -> int:
        if not self._c.collection_exists(self._collection):
            return 0
        return self._c.count(
            collection_name=self._collection,
            count_filter=self._filter(persona_id, record_type),
            exact=True,
        ).count

    def purge(self, persona_id: str) -> None:
        if not self._c.collection_exists(self._collection):
            return
        self._c.delete(
            collection_name=self._collection,
            points_selector=FilterSelector(filter=self._filter(persona_id, None)),
        )
