from dynamo.command.quality import (ChangeNameCommand, ChangeNoValueCommand,
                                    ChangeUuidCommand)
from dynamo.service import get_packages, get_scripts
from dynamo.service.protocol import IDynamoManager


def execute_no_value(manager: IDynamoManager):
    command = ChangeNoValueCommand(get_packages(manager))
    command.execute()
    command = ChangeNoValueCommand(get_scripts(manager))
    command.execute()


def execute_change_name(manager: IDynamoManager):
    command = ChangeNameCommand(get_packages(manager))
    command.execute()
    command = ChangeNameCommand(get_scripts(manager))
    command.execute()


def execute_change_script_uuid(manager: IDynamoManager):
    command = ChangeUuidCommand(get_scripts(manager))
    command.execute()


def execute_quality_checks(manager: IDynamoManager):
    # execute_no_value()
    execute_change_name(manager)
    execute_change_script_uuid(manager)
