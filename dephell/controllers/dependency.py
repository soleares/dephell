# built-in
import re
from typing import List, Optional, Union

# external
from packaging.requirements import Requirement as PackagingRequirement

# app
from ..links import VCSLink, parse_link
from ..markers import Markers
from ..models.constraint import Constraint
from ..models.dependency import Dependency
from ..models.extra_dependency import ExtraDependency
from ..models.git_specifier import GitSpecifier
from ..repositories import get_repo


# regex for names generated by pipenv
rex_hash = re.compile(r'[a-f0-9]{7}')


class DependencyMaker:
    dep_class = Dependency
    extra_class = ExtraDependency

    @classmethod
    def from_requirement(cls, source, req, *, url=None,
                         editable=False) -> List[Union[Dependency, ExtraDependency]]:
        if type(req) is str:
            req = PackagingRequirement(req)
        # https://github.com/pypa/packaging/blob/master/packaging/requirements.py
        link = parse_link(url or req.url)
        # make constraint
        constraint = Constraint(source, req.specifier)
        if isinstance(link, VCSLink) and link.rev:
            constraint._specs[source.name] = GitSpecifier()
        if req.marker is not None:
            marker = Markers(req.marker)
        else:
            marker = None

        base_dep = cls.dep_class(
            raw_name=req.name,
            constraint=constraint,
            repo=get_repo(link),
            link=link,
            marker=marker,
            editable=editable,
        )
        deps = [base_dep]
        if req.extras:
            for extra in req.extras:
                deps.append(cls.extra_class.from_dep(dep=base_dep, extra=extra))
        return deps

    @classmethod
    def from_params(cls, *, raw_name: str, constraint,
                    url: Optional[str] = None, source: Optional['Dependency'] = None,
                    repo=None, marker=None, extras: Optional[List[str]] = None,
                    **kwargs) -> List[Union[Dependency, ExtraDependency]]:
        # make link
        link = parse_link(url)
        if link and link.name and rex_hash.fullmatch(raw_name):
            raw_name = link.name
        # make constraint
        if source:
            constraint = Constraint(source, constraint)
            if isinstance(link, VCSLink) and link.rev:
                constraint._specs[source.name] = GitSpecifier()
        # make repo
        if repo is None:
            repo = get_repo(link)
        if marker is not None:
            marker = Markers(marker)
        base_dep = cls.dep_class(
            link=link,
            repo=repo,
            raw_name=raw_name,
            constraint=constraint,
            marker=marker,
            **kwargs,
        )
        deps = [base_dep]
        if extras:
            for extra in extras:
                deps.append(cls.extra_class.from_dep(dep=base_dep, extra=extra))
        return deps
