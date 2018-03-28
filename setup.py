from setuptools import setup, find_packages

setup(
    name='aiy-voice-only',
    version='1',
    author='Nick Lee',
    author_email='lee1nick@yahoo.ca',
    packages=find_packages(),
    url="https://github.com/nickoala/aiy-voice-only",
    license='LICENSE.txt',
    description="Use AIY Voice Kit's Software without the Shackle of its Hardware",
    install_requires=[
        'google-assistant-library==0.1.0',
        'google-assistant-grpc==0.1.0',
        'google-cloud-speech==0.30.0',
        'google-auth-oauthlib==0.2.0',
        'pyasn1==0.4.2',
        'grpcio==1.7.0',
    ],
    python_requires='~=3.5',
)
