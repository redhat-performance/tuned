#!/usr/bin/env python3
import argparse
import ast
import os
import inspect


class DocLoader:
    def __init__(self, directory, prefix, base):
        self._directory = directory
        self._prefix = prefix
        self._base = base

    def _load_doc(self, module_path):
        with open(module_path, "r") as file:
            tree = ast.parse(file.read(), filename=module_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                hasattr(base, "attr") and base.attr == self._base for base in node.bases
            ):
                return inspect.cleandoc(ast.get_docstring(node))
        return ""

    def load_all_docs(self):
        docs = {}
        for filename in os.listdir(self._directory):
            if not filename.startswith(self._prefix):
                continue
            name = filename.split(".")[0].split("_", 1)[1]
            path = os.path.join(self._directory, filename)
            docs[name] = self._load_doc(path)
        return docs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("prefix")
    parser.add_argument("base")
    parser.add_argument("intro")
    parser.add_argument("out")
    args = parser.parse_args()

    with open(args.intro, "r") as intro_file:
        intro = intro_file.read()

    doc_loader = DocLoader(args.directory, args.prefix, args.base)
    class_docs = doc_loader.load_all_docs()

    with open(args.out, "w") as out_file:
        out_file.write(intro)
        for name, docs in class_docs.items():
            out_file.writelines(["\n", "== **%s**\n" % name, "%s\n" % docs])
