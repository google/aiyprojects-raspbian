from distutils.core import setup

setup(
    name='aiy',
    version='0.1dev',
    author='Peter Malkin',
    author_email='petermalkin@google.com',
    packages=[
        'aiy', 'aiy._apis', 'aiy._drivers', 'aiy.assistant', 'aiy.vision',
        'aiy.vision.models', 'aiy.vision.proto', 'aiy.test'
    ],
    url="https://aiyprojects.withgoogle.com/",
    license='LICENSE.txt',
    description="AIY Python API",
    data_files=[
        ('share/doc/aiy', ['README.md']),
        ('share/doc/aiy/examples', [
            "examples/congratulations.track",
            "examples/dramatic.track",
            "examples/laughing.track",
            "examples/sadtrombone.track",
            "examples/tetris.track",
        ])
    ],
    long_description=open('README.md').read(),
    scripts=[
        "assistant_grpc_demo.py", "assistant_library_with_button_demo.py",
        "cloudspeech_demo.py", "assistant_library_demo.py",
        "assistant_library_with_local_commands_demo.py",
        "examples/buzzer_demo.py",
        "examples/buzzer_tracker_demo.py",
        "examples/vision/joy/joy_detection_demo.py",
        "examples/vision/annotator.py",
        "examples/vision/face_detection.py",
        "examples/vision/face_camera_trigger.py",
        "examples/vision/object_detection.py",
        "examples/vision/face_detection_camera.py",
        "examples/vision/image_classification.py",
        "examples/vision/gpiozero/button_example.py",
        "examples/vision/gpiozero/hat_button.py",
        "examples/vision/gpiozero/simple_button_example.py",
        "examples/vision/gpiozero/led_example.py",
        "examples/vision/gpiozero/servo_example.py"
    ])
