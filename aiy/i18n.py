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

"""Internationalization helpers."""

import gettext

_DEFAULT_LANGUAGE_CODE = 'en-US'
_LOCALE_DOMAIN = 'voice-recognizer'

_language_code = _DEFAULT_LANGUAGE_CODE

_locale_dir = None


def set_locale_dir(locale_dir):
    """Sets the directory that contains the language bundles.

    This is only required if you call set_language_code with gettext_install=True.
    """
    global _locale_dir
    if not locale_dir:
        raise ValueError('locale_dir must be valid')
    _locale_dir = locale_dir


def set_language_code(code, gettext_install=False):
    """Set the BCP-47 language code that the speech systems should use.

    Args:
      gettext_install: if True, gettext's _() will be installed in as a builtin.
          As this has global effect, it should only be done by applications.
    """
    global _language_code
    _language_code = code.replace('_', '-')

    if gettext_install:
        if not _locale_dir:
            raise ValueError('locale_dir is not set. Please call set_locale_dir().')
        language_id = code.replace('-', '_')
        t = gettext.translation(_LOCALE_DOMAIN, _locale_dir, [language_id], fallback=True)
        t.install()


def get_language_code():
    """Returns the BCP-47 language code that the speech systems should use.

    We don't use the system locale because the Assistant API only supports
    en-US at launch, so that should be used by default in all environments.
    """
    return _language_code
