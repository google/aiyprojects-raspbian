#!/usr/bin/env python3
# Copyright 2018 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utility for grouping ImageNet classifications under super-categories.

Super categories are defined by the mapping_data.py file which uses labels from
nodes above the grouped leaves in the wordnet for defining super-categories.
"""

from .mapping_data import CATEGORIES
from .mapping_data import MAPPINGS


def get_category(word):
    return MAPPINGS.get(word)


def get_categories():
    return CATEGORIES


def get_word_index(word):
    category = get_category(word)
    if category is None:
        return -1
    return get_categories().index(category)


def get_category_index(category):
    try:
        return get_categories().index(category)
    except ValueError:
        return -1


def _example_usage():
    """Example usage for the category mapper utility."""
    print('~'.join(get_categories()))
    print(get_category('hay'))
    print(get_category('ballpoint/ballpoint pen/ballpen/Biro'))
    print(get_category('beer bottle'))
    print(get_category('NASDFOIAAS'))
    print(get_word_index('beer bottle'))
    print(get_word_index('NASDFLJ'))
    for cat in get_categories():
        print('%d : %s' % (get_category_index(cat), cat))

    cat = 'Other'
    print('%d : %s' % (get_category_index(cat), cat))


if __name__ == '__main__':
    _example_usage()
