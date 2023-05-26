import math as m

from dynamo.models.model import IModelWithId


def get_distance(point: IModelWithId, other: IModelWithId):
    result = m.pow(point.x - other.x, 2) + m.pow(point.y - other.y, 2)
    return m.sqrt(result)


def is_within(point: IModelWithId, other: IModelWithId, offset: float):
    return get_distance(point, other) < offset
