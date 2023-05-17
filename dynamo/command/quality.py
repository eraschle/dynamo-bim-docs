from dataclasses import fields
from typing import Any, Dict, Iterable, List, Protocol
from uuid import uuid4

from dynamo.models.files import AFileBaseModel, Script
from dynamo.models.nodes import ABaseModel
from dynamo.utils.checks import is_blank


class Command(Protocol):

    def execute(self):
        pass


class ChangeNoValueCommand(Command):

    default_values = {
        str: 'DOC_DEFAULT_VALUE',
        list: ['DOC_DEFAULT_VALUE']
    }

    def __init__(self, models: Iterable[ABaseModel]) -> None:
        super().__init__()
        self.models = models

    def change_no_value_if_base_model(self, model: Any):
        if isinstance(model, ABaseModel):
            self.change_no_value(model)

    def change_no_value_if_str(self, model: ABaseModel, attr: str, value: Any):
        if isinstance(value, str) and is_blank(value):
            setattr(model, attr, self.default_values[str])

    def change_no_value_if_list(self, model: ABaseModel, attr: str, value: Any):
        if not isinstance(value, list) or isinstance(value, str):
            return
        if len(value) == 0:
            setattr(model, attr, self.default_values[list])
        else:
            self.change_no_value_in_list(value)

    def change_no_value_in_list(self, models: Iterable[Any]):
        for model in models:
            self.change_no_value_if_base_model(model)

    def change_no_value(self, model: ABaseModel):
        for field in fields(model):
            value = getattr(model, field.name)
            self.change_no_value_if_base_model(value)
            self.change_no_value_if_str(model, field.name, value)
            self.change_no_value_if_list(model, field.name, value)

    def execute(self):
        for model in self.models:
            self.change_no_value(model)


class ChangeNameCommand(Command):

    def __init__(self, models: Iterable[AFileBaseModel]) -> None:
        super().__init__()
        self.models = models

    def execute(self):
        for model in self.models:
            if model.name == model.path.stem:
                continue
            print(f'Changed name from "{model.name}" to "{model.path.stem}"')
            model.name = model.path.stem


class ChangeUuidCommand(Command):

    def __init__(self, scripts: Iterable[Script]) -> None:
        super().__init__()
        self.scripts = scripts

    def _uuid_dict(self) -> Dict[str, List[Script]]:
        uuid_dict = {}
        for script in self.scripts:
            if script.uuid not in uuid_dict:
                uuid_dict[script.uuid] = []
            uuid_dict[script.uuid].append(script)
        return uuid_dict

    def execute(self):
        for uuid, scripts in self._uuid_dict().items():
            if len(scripts) < 2:
                continue
            print(f'{len(scripts)} have UUID "{uuid}"')
            for script in scripts[1:]:
                script.uuid = str(uuid4())
