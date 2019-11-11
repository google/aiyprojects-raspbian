MAKEFILE_DIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON=python3

.PHONY: help
help:
	@echo "make help                 - Show all make targets"
	@echo "make test-vision-images   - Download vision test images"
	@echo "make test-vision-driver   - Run vision driver tests"
	@echo "make test-vision-latency  - Run vision latency tests"
	@echo "make test-vision-models   - Run vision model tests"
	@echo "make test-vision-examples - Run vision example tests"
	@echo "make test-vision          - Run all vision tests"
	@echo "make docs                 - Generate documentation"
	@echo "make docs-clean           - Remove generated documentation"
	@echo "make docs-open            - Open generated documentation"
	@echo "make joy-demo-start       - Start JoyDemo service"
	@echo "make joy-demo-stop        - Stop JoyDemo service"
	@echo "make joy-demo-restart     - Restart JoyDemo service"
	@echo "make joy-demo-enable      - Enable JoyDemo service"
	@echo "make joy-demo-disable     - Disable JoyDemo service"
	@echo "make joy-demo-log         - Print JoyDemo service log"
	@echo "make lint                 - Run python code linter"
	@echo "make pep8-diff            - Show incorrect code formatting"
	@echo "make clean                - Remove generated files"

.PHONY: test-vision-images \
        test-vision-driver \
        test-vision-latency \
        test-vision-models \
        test-vision-examples \
        test-vision

test-vision-images:
	$(MAKE) -C src/tests/images

VISION_DRIVER_TESTS:=src/tests/spicomm_test.py
VISION_LATENCY_TESTS:=src/tests/camera_inference_latency_test.py
VISION_EXAMPLE_TESTS:=src/tests/vision_examples_test.py
VISION_MODEL_TESTS:=\
	src/tests/engine_test.py \
	src/tests/dish_classification_test.py \
	src/tests/dish_detection_test.py \
	src/tests/face_detection_test.py \
	src/tests/image_classification_test.py \
	src/tests/object_detection_test.py \
	src/tests/inaturalist_classification_test.py

test-vision-driver:
	$(PYTHON) -m unittest -v $(VISION_DRIVER_TESTS)

test-vision-latency:
	$(PYTHON) -m unittest -v $(VISION_LATENCY_TESTS)

test-vision-models: test-vision-images
	$(PYTHON) -m unittest -v $(VISION_MODEL_TESTS)

test-vision-examples: test-vision-images
	$(PYTHON) -m unittest -v $(VISION_EXAMPLE_TESTS)

test-vision: test-vision-images
	$(PYTHON) -m unittest -v \
		$(VISION_DRIVER_TESTS) \
		$(VISION_LATENCY_TESTS) \
		$(VISION_MODEL_TESTS) \
		$(VISION_EXAMPLE_TESTS)

.PHONY: docs docs-clean docs-open
docs:
	sphinx-build -b html $(MAKEFILE_DIR)/docs $(MAKEFILE_DIR)/docs/_build/html

docs-clean:
	rm -rf $(MAKEFILE_DIR)/docs/_build

docs-open:
	$(PYTHON) -m webbrowser -t "file://$(MAKEFILE_DIR)/docs/_build/html/index.html"

.PHONY: joy-demo-log

joy-demo-%:
	sudo systemctl $* joy_detection_demo.service

joy-demo-log:
	sudo journalctl -u joy_detection_demo.service -b -f

.PHONY: lint pep8-diff
lint:
	find src -iname "*.py" | grep -v pb2 | xargs $(PYTHON) -m pylint --rcfile .pylintrc

pep8-diff:
	$(PYTHON) -m autopep8 --max-line-length=100 --diff `find src -iname "*.py" | grep -v pb2`

.PHONY: clean
clean:
	rm -f $(MAKEFILE_DIR)/src/tests/images/*.jpg
