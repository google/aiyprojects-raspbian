# Copyright 2017 Google Inc.
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
from collections import OrderedDict


def rgb(color):
    return 'rgb(%s, %s, %s)' % color


class Tag:
    NAME = None
    REQUIRED_ATTRS = ()

    def __init__(self, attrs=None):
        self._attrs = OrderedDict()

        for attr in self.REQUIRED_ATTRS:
            if attr not in attrs:
                raise ValueError('Missing attribute "%s" from tag <%s/>' % (attr, self.NAME))

        for key, value in attrs.items():
          self._attrs[key.replace('_', '-')] = value

    @property
    def value(self):
        return None

    def __str__(self):
        sattrs = ' '.join('%s="%s"' % (name, value) for name, value in self._attrs.items())
        if sattrs:
            sattrs = ' ' + sattrs
        v = self.value
        if v is None:
            return '<%s%s/>' % (self.NAME, sattrs)

        return '<%s%s>%s</%s>' % (self.NAME, sattrs, v, self.NAME)


class TagContainer(Tag):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self._children = []

    def add(self, child):
        self._children.append(child)
        return child

    @property
    def value(self):
        return ''.join(str(child) for child in self._children)

class Svg(TagContainer):
    NAME = 'svg'

    def __init__(self, **kwargs):
        super().__init__({'xmlns':'http://www.w3.org/2000/svg', **kwargs})


class Group(TagContainer):
    NAME = 'g'

    def __init__(self, **kwargs):
        super().__init__(kwargs)


class Line(Tag):
    NAME = 'line'
    REQUIRED_ATTRS = ('x1', 'y1', 'x2', 'y2')

    def __init__(self, **kwargs):
        super().__init__(kwargs)


class Rect(Tag):
    NAME = 'rect'
    REQUIRED_ATTRS = ('x', 'y', 'width', 'height')

    def __init__(self, **kwargs):
        super().__init__(kwargs)


class Circle(Tag):
    NAME = 'circle'
    REQUIRED_ATTRS = ('cx', 'cy', 'r')

    def __init__(self, **kwargs):
        super().__init__(kwargs)


class Ellipse(Tag):
    NAME = 'ellipse'
    REQUIRED_ATTRS = ('cx', 'cy', 'rx', 'ry')

    def __init__(self, **kwargs):
        super().__init__(kwargs)


class Text(Tag):
    NAME = 'text'
    REQUIRED_ATTRS = ('x', 'y')

    def __init__(self, text, **kwargs):
        super().__init__(kwargs)
        self._text = text

    @property
    def value(self):
        return self._text
