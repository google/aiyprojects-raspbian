aiy.assistant
=============

APIs that simplify interaction with the
`Google Assistant API`_ in one of two ways:
using either :mod:`aiy.assistant.grpc` or :mod:`aiy.assistant.library`, corresponding to the
`Google Assistant Service`_ and `Google Assistant Library`_, respectively.

Which of these you choose may depend on your intentions.
The Google Assistant Service provides a gRPC interface that is generally more complicated. However,
the :mod:`aiy.assistant.grpc` API offered here does not provide access to those APIs. Instead, it
completely wraps the |code| :assistant-rpc:`google.assistant.embedded.v1alpha2`\ |endcode| APIs. It
takes care of all the complicated setup for you, and handles all response events. Thus, if all you
want to build a basic version of the Google Assistant, then using :mod:`aiy.assistant.grpc`
is easiest because it requires the least amount of code.
For an example, see :github:`src/examples/voice/assistant_grpc_demo.py`.

On the other hand, :mod:`aiy.assistant.library` is a thin wrapper around
|code| :assistant:`google.assistant.library<>`\ |endcode|. It overrides the ``Assistant.start()``
method to handle the device registration, but beyond that, you can and must use the
|code| :assistant:`google.assistant.library<>`\ |endcode| APIs to respond to all events returned by
the Google Assistant. As such, using :mod:`aiy.assistant.library` provides you more control,
allowing you to build custom device commands based on conversation with the Google Assistant.
For an example, see :github:`src/examples/voice/assistant_library_with_local_commands_demo.py`.

Additionally, only :mod:`aiy.assistant.library` includes built-in support for hotword detection
(such as "Okay Google"). However, if you're using the Raspberry Pi Zero (provided with the V2 Voice
Kit), then you cannot use hotword detection because that feature depends on the ARMv7 architecture
and the Pi Zero has only ARMv6. So that feature of the library works only with Raspberry Pi 2/3,
and if you're using a Pi Zero, you must instead use the button or another type of trigger to
initiate a conversation with the Google Assistant. (Note: The Voice Bonnet can be used on
any Raspberry Pi.)

**Tip:** If all you want to do is create custom voice commands (such as "turn on the light"), then
you don't need to interact with the Google Assistant. Instead, you can use :mod:`aiy.cloudspeech`
to convert your voice commands into text that triggers your actions.

.. note::

    These APIs are designed for the Voice Kit, but have no dependency on the Voice
    HAT/Bonnet specifically. However, they do require some type of sound card
    attached to the Raspberry Pi that can be detected by the ALSA subsystem.

.. _Google Assistant API: https://developers.google.com/assistant/sdk/
.. _Google Assistant Service: https://developers.google.com/assistant/sdk/guides/service/python/
.. _Google Assistant Library: https://developers.google.com/assistant/sdk/guides/library/python/

.. include:: directives.txt

aiy.assistant.grpc
------------------

.. automodule:: aiy.assistant.grpc
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:


aiy.assistant.library
---------------------

.. automodule:: aiy.assistant.library
    :members:
    :undoc-members:


aiy.assistant.auth\_helpers
---------------------------

.. automodule:: aiy.assistant.auth_helpers
    :members:
    :undoc-members:
    :show-inheritance: