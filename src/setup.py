from setuptools import setup, find_packages

setup(
    name='aiy-projects-python',
    version='1.1',
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
        'google-assistant-grpc==0.1.0',
        'google-assistant-library==0.1.0',
        'google-cloud-speech==0.30.0',
        'gpiozero',
        'paho-mqtt',
        'picamera',
        'pillow',
        'RPi.GPIO',
    ],
    python_requires='>=3.5.0',
)
