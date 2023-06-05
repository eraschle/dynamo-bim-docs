from typing import Dict, List, Protocol
from uuid import uuid4

from dynamo.models.files import Script
from dynamo.source.gateway import INodeGateway


class Command(Protocol):

    def execute(self):
        pass


class AScriptQualityCommand(Command):

    def __init__(self, gateway: INodeGateway) -> None:
        super().__init__()
        self.gateway = gateway


class ChangeScriptNameCommand(AScriptQualityCommand):

    def execute(self):
        for script in self.gateway.scripts:
            if script.name == script.path.stem:
                continue
            print(f'Changed name from "{script.name}" to "{script.path.stem}"')
            self.gateway.change_name(script, script.path.stem)


class ChangeScriptUuidCommand(AScriptQualityCommand):

    def _uuid_dict(self) -> Dict[str, List[Script]]:
        uuid_dict = {}
        for script in self.gateway.scripts:
            if script.uuid not in uuid_dict:
                uuid_dict[script.uuid] = []
            uuid_dict[script.uuid].append(script)
        return uuid_dict

    def execute(self):
        for uuid, scripts in self._uuid_dict().items():
            if len(scripts) <= 1:
                continue
            print(f'{len(scripts)} have same UUID "{uuid}"')
            for script in scripts[1:]:
                new_uuid = str(uuid4())
                print(f'{script.name}: Changed UUID from "{script.uuid}" to "{new_uuid}"')
                self.gateway.change_uuid(script, new_uuid)
