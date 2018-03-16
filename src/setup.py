from setuptools import setup, find_packages

setup(
    name='aiy-projects-python',
    version='1.0',
    author='Peter Malkin',
    author_email='petermalkin@google.com',
    packages=find_packages(),
    url="https://aiyprojects.withgoogle.com/",
    license='LICENSE.txt',
    description="AIY Python API",
    data_files=[
        ('share/doc/aiy', ['README.md']),
        ('share/doc/aiy/examples', [
            "examples/vision/buzzer/congratulations.track",
            "examples/vision/buzzer/dramatic.track",
            "examples/vision/buzzer/laughing.track",
            "examples/vision/buzzer/sadtrombone.track",
            "examples/vision/buzzer/tetris.track",
        ]),
    ],
    install_requires=[
        'google-assistant-grpc>=0.1.0',
        'google-cloud-speech>=0.30.0',
        'google-auth-oauthlib>=0.2.0',
        'pyasn1>=0.4.2',
        'grpcio>=1.7.0',
    ],
    python_requires='~=3.5',
    scripts=[
        "examples/buzzer/buzzer_demo.py",
        "examples/buzzer/buzzer_tracker_demo.py",
        "examples/voice/assistant_grpc_demo.py",
        "examples/voice/assistant_library_demo.py",
        "examples/voice/assistant_library_with_button_demo.py",
        "examples/voice/assistant_library_with_local_commands_demo.py",
        "examples/voice/cloudspeech_demo.py",
    ])
