PYTHON=python3

.PHONY: all test-download test deb clean

all:
	@echo "make lint                 - Run python code linter"
	@echo "make joy-demo-start       - Start JoyDemo service"
	@echo "make joy-demo-stop        - Stop JoyDemo service"
	@echo "make joy-demo-enable      - Enable JoyDemo service"
	@echo "make joy-demo-disable     - Disable JoyDemo service"
	@echo "make test-vision-images   - Download vision test images"
	@echo "make test-vision-driver   - Run vision driver tests"
	@echo "make test-vision-models   - Run vision model tests"
	@echo "make test-vision-examples - Run vision example tests"
	@echo "make test-vision          - Run all vision tests"
	@echo "make clean                - Remove generated files"
	@echo "make deb                  - Generate Debian package"

test-vision-images:
	$(MAKE) -C src/tests/images

test-vision-driver:
	$(PYTHON) -m unittest \
		src/tests/spicomm_test.py

test-vision-latency:
	$(PYTHON) -m unittest \
		src/tests/camera_inference_latency_test.py

test-vision-models: test-vision-images
	$(PYTHON) -m unittest \
		src/tests/dish_classification_test.py \
		src/tests/dish_detection_test.py \
		src/tests/face_detection_test.py \
		src/tests/image_classification_test.py \
		src/tests/object_detection_test.py

test-vision-examples: test-vision-images
	$(PYTHON) -m unittest \
		src/tests/vision_examples_test.py

test-vision: \
	test-vision-driver \
	test-vision-latency \
	test-vision-models \
	test-vision-examples

deb:
	dpkg-buildpackage -b -rfakeroot -us -uc -tc

lint:
	find src -iname "*.py" | grep -v pb2 | xargs $(PYTHON) -m pylint --rcfile .pylintrc

# enable, disable, start, stop, restart, status
joy-demo-%:
	sudo systemctl $* joy_detection_demo.service

joy-demo-log:
	journalctl -u joy_detection_demo.service -b -f

clean:
	rm -f $(CURDIR)/src/tests/images/*.jpg
