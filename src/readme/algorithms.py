#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Time:
    2022-09-28 20:19
Author:
    huayang (imhuay@163.com)
Subject:
    algo
"""
from __future__ import annotations

# import os
# import sys
# import unittest
import json
import os
import re

from typing import ClassVar
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field

from huaytools.utils import get_logger, MarkdownUtils


@dataclass
class ProblemInfo:
    category: list[str]
    source: str
    number: str
    level: str
    name: str
    company: list[str]
    file_path: Path

    # field_name
    F_CATEGORY: ClassVar[str] = 'category'
    F_SOURCE: ClassVar[str] = 'source'
    F_NUMBER: ClassVar[str] = 'number'
    F_LEVEL: ClassVar[str] = 'level'
    F_NAME: ClassVar[str] = 'name'
    F_COMPANY: ClassVar[str] = 'company'
    F_PATH: ClassVar[str] = f'file_path'

    @property
    def head_name(self):
        return self.file_path.stem


@dataclass(unsafe_hash=True)
class TagTypeInfo:
    name: str
    show_name: str
    level: int


class TagType:
    hot: ClassVar[TagTypeInfo] = TagTypeInfo('hot', 'Hot 🔥', 0)
    level: ClassVar[TagTypeInfo] = TagTypeInfo(ProblemInfo.F_LEVEL, 'Level', 1)
    subject: ClassVar[TagTypeInfo] = TagTypeInfo(ProblemInfo.F_SOURCE, 'Subject', 2)
    category: ClassVar[TagTypeInfo] = TagTypeInfo(ProblemInfo.F_CATEGORY, 'Category', 3)


@dataclass
class TagInfo:
    tag_name: str
    tag_type: TagTypeInfo = None
    collects: list[ProblemInfo] = field(default_factory=list)

    @property
    def tag_count(self):
        return len(self.collects)

    EMPTY: ClassVar[str] = ''

    @property
    def tag_category(self):
        if '-' in self.tag_name:
            return self.tag_name.split('-', maxsplit=1)[0]
        else:
            return self.EMPTY

    @property
    def tag_head(self):
        if '-' in self.tag_name:
            name = self.tag_name.split('-', maxsplit=1)[1]
        else:
            name = self.tag_name
        return f'{name} ({self.tag_count})'


# 修改 tag 的类型
TAG2TYPE_MODIFY = {
    '热门&经典&易错': TagType.hot
}
# 加入热门标签
EX_HOT_TAGS = [
    'LeetCode',
    '剑指Offer',
    '牛客'
]


class AlgoReadme:
    """"""
    logger = get_logger()
    # AUTO_GENERATED_STR = '<!-- Auto-generated -->'
    RE_INFO = re.compile(r'<!--(.*?)-->', flags=re.DOTALL)

    def __init__(self, fp_algo: Path):
        """"""
        # attrs
        self.fp_algo = fp_algo
        self.fp_problems = fp_algo / 'problems'
        self.fp_toc = fp_algo / 'toc'
        with open(self.fp_algo / 'tag2topic.json') as f:
            self.tag2topic = json.load(f)

        # pipeline
        self._extract_infos()
        self._collect_tags()
        # self.generate_readme()

    problems_infos: list[ProblemInfo] = []

    def _extract_infos(self):
        """"""
        for dp, _, fns in os.walk(self.fp_problems):
            for fn in fns:
                fp = Path(dp) / fn  # each problem.md
                if fp.suffix != '.md':
                    continue
                info = self._extract_info(fp)
                self._update_info(info, fp)
                self._try_update_title(info)
                self.problems_infos.append(ProblemInfo(**info))

    def _update_info(self, info, fp):
        """"""
        # update standard tag
        new_tags = []
        for tag in info[ProblemInfo.F_CATEGORY]:
            new_tags.append(self.tag2topic[tag.lower()])
        info[ProblemInfo.F_CATEGORY] = new_tags

        # add fp
        fp = self._try_rename(fp, info)
        info[ProblemInfo.F_PATH] = fp

    TEMPLATE_PROBLEM_TITLE = '## {src}_{no}_{title}（{level}, {date}）'

    def _try_update_title(self, info) -> bool:
        """"""
        fp = info[ProblemInfo.F_PATH]
        new_title = self.TEMPLATE_PROBLEM_TITLE.format(src=info[ProblemInfo.F_SOURCE],
                                                       no=info[ProblemInfo.F_NUMBER],
                                                       title=info[ProblemInfo.F_NAME],
                                                       level=info[ProblemInfo.F_LEVEL],
                                                       date='-'.join(str(fp.parent).split('/')[-2:]))
        with fp.open(encoding='utf8') as f:
            lines = f.read().split('\n')

        updated = True
        if not lines[0].startswith('##'):
            lines.insert(0, new_title)
        elif lines[0] != new_title:
            lines[0] = new_title
        else:
            updated = False

        if updated:
            with fp.open('w', encoding='utf8') as f:
                f.write('\n'.join(lines))
            self._git_add(fp)

        return updated

    TEMPLATE_PROBLEM_FILENAME = '{src}_{no}_{level}_{title}.md'

    def _try_rename(self, fp: Path, info) -> Path:
        """"""
        new_fn = self.TEMPLATE_PROBLEM_FILENAME.format(src=info[ProblemInfo.F_SOURCE],
                                                       no=info[ProblemInfo.F_NUMBER],
                                                       level=info[ProblemInfo.F_LEVEL],
                                                       title=info[ProblemInfo.F_NAME])
        if new_fn != fp.name:
            self.logger.info(f'rename {fp.name} to {new_fn}')
            fp = fp.rename(fp.parent / new_fn)
            self._git_add(fp)

        return fp

    NUMBER_WIDTH = 5

    def _extract_info(self, fp) -> dict:
        """"""
        fp = Path(fp)
        with fp.open(encoding='utf8') as f:
            txt = f.read()

        try:
            info_str = self.RE_INFO.search(txt).group(1)
            info = json.loads(info_str)
            return info
        except:  # noqa
            self.logger.info(fp)

    GIT_ADD_TEMP = 'git add "{fp}"'

    def _git_add(self, fp):
        """"""
        command = self.GIT_ADD_TEMP.format(fp=fp)
        # self.logger.info(command)
        os.system(command)

    tag_infos: dict[str, TagInfo] = dict()

    def _collect_tags(self):
        """"""

        def _add(_tag, _type, _info):
            _type = TAG2TYPE_MODIFY.get(_tag, _type)
            if _tag not in self.tag_infos:
                self.tag_infos[_tag] = TagInfo(_tag)
                self.tag_infos[_tag].tag_type = _type
            else:
                assert self.tag_infos[_tag].tag_type == _type
            self.tag_infos[_tag].collects.append(_info)

        for problems_info in self.problems_infos:
            _add(problems_info.source, TagType.subject, problems_info)
            _add(problems_info.level, TagType.level, problems_info)
            for cat in problems_info.category:
                _add(cat, TagType.category, problems_info)

        # sort
        for info in self.tag_infos.values():
            info.collects.sort(key=lambda i: (i.source, i.number))

    hot_toc: list[str]
    type2tags: dict[TagTypeInfo, list[TagInfo]] = defaultdict(list)

    @staticmethod
    def _get_toc_tag_line(tag_info):
        """"""
        return f'- [{tag_info.tag_head}](#{MarkdownUtils.slugify(tag_info.tag_head)})'

    def _generate_sub_toc(self, tag_type: TagTypeInfo):
        """"""
        sub_toc = [f'## {tag_type.show_name}']
        for tag_info in self.type2tags[tag_type]:
            sub_toc.append(self._get_toc_tag_line(tag_info))
        return sub_toc

    def _generate_category_toc(self):
        """"""
        category2problems = defaultdict(list)
        for tag_info in self.type2tags[TagType.category]:
            assert tag_info.tag_category != ''
            category2problems[tag_info.tag_category].append(tag_info)

        toc = [f'## {TagType.category.show_name}']
        for tag_category, tag_infos in category2problems.items():
            toc.append(f'### {tag_category}')
            for tag_info in tag_infos:
                toc.append(self._get_toc_tag_line(tag_info))
        return toc

    def build(self):
        """"""
        for tag, tag_info in self.tag_infos.items():
            self.type2tags[tag_info.tag_type].append(tag_info)
        for tag_infos in self.type2tags.values():
            tag_infos.sort(key=lambda i: (i.tag_category, -i.tag_count, i.tag_name))

        # sub toc
        self.hot_toc = toc_hot = self._generate_sub_toc(TagType.hot)
        for tag in EX_HOT_TAGS:
            tag_info = self.tag_infos[tag]
            toc_hot.append(self._get_toc_tag_line(tag_info))
        toc_level = self._generate_sub_toc(TagType.level)
        toc_subject = self._generate_sub_toc(TagType.subject)
        toc_category = self._generate_category_toc()

        contents = []
        for tag_type in sorted(self.type2tags.keys(), key=lambda i: i.level):
            tag_infos = self.type2tags[tag_type]
            for tag_info in tag_infos:
                contents.append(f'### {tag_info.tag_head}')
                for problem_info in tag_info.collects:
                    contents.append('- [`{name}`]({path})'.format(
                        name=problem_info.head_name,
                        path=problem_info.file_path.relative_to(self.fp_algo)
                    ))
                contents.append('')

        with open(self.fp_algo / 'README.md', 'w', encoding='utf8') as f:
            f.write('# Algorithms Coding\n\n')
            f.write('\n'.join(toc_hot))
            f.write('\n')
            f.write('\n'.join(toc_level))
            f.write('\n')
            f.write('\n'.join(toc_subject))
            f.write('\n')
            f.write('\n'.join(toc_category))
            f.write('\n\n---\n\n')
            f.write('\n'.join(contents))


if __name__ == '__main__':
    """"""
    _fp = Path(r'/home/huay/workspace/github/studies/algorithms')
    algo = AlgoReadme(_fp)
    algo.build()
