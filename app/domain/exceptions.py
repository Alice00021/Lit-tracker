class NotFoundError(Exception):
    def __init__(self, entity: str, entity_id: int):
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} с id={entity_id} не найден")