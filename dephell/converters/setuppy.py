# built-in
from distutils.core import run_setup
from itertools import chain

# external
from packaging.requirements import Requirement

# app
from ..models import Dependency, RootDependency, Author
from .base import BaseConverter


TEMPLATE = """
# -*- coding: utf-8 -*-
from distutils.core import setup
import os.path


long_description = ''
for name in ('README.rst', 'README.md'):
    if not os.path.exists(name):
        with open(name, encoding='utf8') as stream:
            long_description = stream.read()
        break

setup(
    long_description=long_description,
    {kwargs},
)
"""


class SetupPyConverter(BaseConverter):
    lock = False

    @classmethod
    def load(cls, path) -> RootDependency:
        info = run_setup(str(path))

        root = RootDependency(
            raw_name=cls._get(info, 'name'),
            version=cls._get(info, 'version') or '0.0.0',

            description=cls._get(info, 'summary'),
            license=cls._get(info, 'license'),
            long_description=cls._get(info, 'description'),

            keywords=cls._get(info, 'keywords').split(','),
            classifiers=cls._get_list(info, 'classifiers'),
            platforms=cls._get_list(info, 'platforms'),
        )

        # links
        for key, name in (('home', 'url'), ('download', 'download_url')):
            link = cls._get(info, name)
            if link:
                root.links[key] = link

        # authors
        for name in ('author', 'maintainer'):
            author = cls._get(info, name)
            if author:
                root.authors += (
                    Author(name=author, mail=cls._get(info, name + '_email')),
                )

        reqs = chain(
            cls._get_list(info, 'requires'),
            cls._get_list(info, 'install_requires'),
        )
        deps = []
        for req in reqs:
            req = Requirement(req)
            deps.append(Dependency.from_requirement(source=root, req=req))
        root.attach_dependencies(deps)
        return root

    def dumps(self, reqs, project: RootDependency, content=None) -> str:
        """
        https://setuptools.readthedocs.io/en/latest/setuptools.html?highlight=long_description#metadata
        """
        content = []
        content.append(('name', project.raw_name))
        content.append(('version', project.version))
        if project.description:
            content.append(('description', project.description))

        # links
        fields = (
            ('home', 'url'),
            ('download', 'download_url'),
        )
        for key, name in fields:
            if key in project.links:
                content.append((name, project.links[key]))
        if project.links:
            content.append(('project_urls', project.links))

        # authors
        if project.authors:
            author = project.authors[0]
            content.append(('author', author.name))
            content.append(('author_email', author.mail))
        if len(project.authors) > 1:
            author = project.authors[1]
            content.append(('maintainer', author.name))
            content.append(('maintainer_email', author.mail))

        if project.license:
            content.append(('license', project.license))
        if project.keywords:
            content.append(('keywords', ' '.join(project.keywords)))
        if project.classifiers:
            content.append(('classifiers', project.classifiers))
        if project.platforms:
            content.append(('platforms', project.platforms))

        reqs_list = [self._format_req(req=req) for req in reqs]
        content.append(('requires', reqs_list))

        content = ',\n    '.join(
            '{}={!r}'.format(name, value) for name, value in content,
        )
        return content

    # private methods

    @staticmethod
    def _get(msg, name: str) -> str:
        value = getattr(msg.metadata, name, None)
        if not value:
            value = getattr(msg, name, None)
        if not value:
            return ''
        if value == 'UNKNOWN':
            return ''
        return value.strip()

    @staticmethod
    def _get_list(msg, name: str) -> tuple:
        values = getattr(msg, name, None)
        if not values:
            return ()
        return tuple(value for value in values if value != 'UNKNOWN')
