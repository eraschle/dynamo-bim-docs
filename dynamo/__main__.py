import os
from pathlib import Path
from typing import Iterable, List

from dynamo.command import quality
from dynamo.docs import custom, manager, package, script
from dynamo.docs.doc_models import (CustomNodeDocFile, PackageDocFile,
                                    ScriptDocFile)
from dynamo.docs.docs import IDocsFile, IDocsManager
from dynamo.models.files import Package
from dynamo.service import dynamo, json_gateway
from dynamo.service.protocol import IDynamoManager
from dynamo.source.gateway import INodeGateway


def _documentation_packages(gateway: INodeGateway, manager: IDocsManager, with_code_block: bool) -> List[IDocsFile]:
    doc_files = []
    for package_file in gateway.read_packages([manager.package_src_path]):
        doc_file = PackageDocFile(package_file, manager)
        doc_files.append(doc_file)
        package.get_docs(doc_file)
        doc_files.extend(_documentation_custom_nodes(package_file, manager, with_code_block))
    return doc_files


def _documentation_custom_nodes(package: Package, manager: IDocsManager, with_code_block: bool) -> Iterable[IDocsFile]:
    doc_files = []
    for custom_file in package.nodes:
        doc_file = CustomNodeDocFile(custom_file, manager)
        doc_files.append(doc_file)
        custom.get_docs(doc_file, with_code_block)
    return doc_files


def script_quality_checks(gateway: INodeGateway):
    quality.ChangeScriptUuidCommand(gateway).execute()
    quality.ChangeScriptNameCommand(gateway).execute()


def _documentation_scripts(manager: IDocsManager, gateway: INodeGateway, with_code_block: bool) -> Iterable[IDocsFile]:
    doc_files = []
    gateway.read_scripts([manager.script_src_path])
    script_quality_checks(gateway)
    for script_file in gateway.scripts:
        doc_file = ScriptDocFile(script_file, manager)
        doc_files.append(doc_file)
        script.get_docs(doc_file, with_code_block)
    return doc_files


def _documentation_get_old(manager: IDocsManager, gateway: INodeGateway, doc_files: Iterable[IDocsFile]) -> Iterable[Path]:
    all_doc_files = gateway.documentations([manager.script_doc_path, manager.package_doc_path])
    for doc_file in doc_files:
        doc_path = doc_file.doc_path
        if doc_path not in all_doc_files:
            continue
        all_doc_files.remove(doc_path)
    return all_doc_files


def _documentation_remove(manager: IDocsManager, gateway: INodeGateway, doc_files: Iterable[IDocsFile]) -> None:
    for path in _documentation_get_old(manager, gateway, doc_files):
        os.remove(path)
    html_root_path = manager.doc_root.parent / 'html'
    html_paths = gateway.html_documentations([html_root_path])
    for path in [path for path in html_paths if path.is_file()]:
        os.remove(path)
    dir_paths = [path for path in html_paths if path.is_dir()]
    dir_paths.reverse()
    for path in dir_paths:
        if not path.exists():
            continue
        os.removedirs(path)


def documentation(dynamo: IDynamoManager, gateway: INodeGateway, with_code_block: bool):
    docs_manager = manager.create_docs(dynamo)
    files = _documentation_packages(gateway, docs_manager, with_code_block)
    files.extend(_documentation_scripts(docs_manager, gateway, with_code_block))
    _documentation_remove(docs_manager, gateway, files)


def main():
    manager = dynamo.get_manager()
    gateway = json_gateway(manager)
    documentation(manager, gateway, with_code_block=False)


if __name__ == '__main__':
    main()
