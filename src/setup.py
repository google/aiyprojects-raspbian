from setuptools import setup, find_packages

setup(
    name='aiy-projects-python',
    version='1.2',
    description='AIY Python API',
    author='AIY Team',
    author_email='support-aiyprojects@google.com',
    url="https://aiyprojects.withgoogle.com/",
    project_urls={
        'GitHub: issues': 'https://github.com/google/aiyprojects-raspbian/issues',
        'GitHub: repo': 'https://github.com/google/aiyprojects-raspbian',
    },
    license='Apache 2',
    packages=find_packages(),
    install_requires=[
        'google-assistant-library==1.0.1',
        'google-assistant-grpc==0.2.0',
        'google-auth==1.5.1',
        'google-auth-oauthlib==0.2.0',
        'google-cloud-speech==0.36.0',
        'gpiozero',
        'paho-mqtt',
        'protobuf==3.6.1',
        'picamera',
        'pillow',
        'RPi.GPIO',
    ],
    python_requires='>=3.5.3',
)
