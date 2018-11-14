# Open Images Dataset V4
all: cat.jpg dog.jpg hotdog.jpg faces.jpg sparrow.jpg bee.jpg lily.jpg

define download_image
	$(eval $1_TMP := $(shell mktemp /tmp/$1.XXXXXX))
	wget -O $($1_TMP) $2
	echo $3 $($1_TMP) | md5sum --check -
	mv $($1_TMP) $1
endef

# License: https://creativecommons.org/licenses/by/2.0/
# URL: https://storage.googleapis.com/openimages/web/visualizer/index.html?set=train&c=%2Fm%2F01yrx&id=818c36d0b603e096
cat.jpg:
	$(call download_image,$@,"https://farm7.staticflickr.com/3712/11270364836_8d1182be97_o.jpg","f08083ddb111a9d5bd6e00d7c04aa97f")

# License: https://creativecommons.org/licenses/by/2.0/
# URL: https://storage.googleapis.com/openimages/web/visualizer/index.html?set=train&c=%2Fm%2F0bt9lr&id=b2e6af69191eb3bf
dog.jpg:
	$(call download_image,$@,"https://c8.staticflickr.com/8/7580/15865399370_3857b60669_o.jpg","416afbfd4bd09758955cdffa2e62a58e")

# License: https://creativecommons.org/licenses/by/2.0/
# URL: https://storage.googleapis.com/openimages/web/visualizer/index.html?set=train&c=%2Fm%2F01b9xk&id=4d7133d6aabede44
hotdog.jpg:
	$(call download_image,$@,"https://farm5.staticflickr.com/7284/16301478750_b036c617cb_o.jpg","cc466191c0844c8da25bbbf63b66bd15")

# License: https://creativecommons.org/licenses/by/2.0/
# URL: https://storage.googleapis.com/openimages/web/visualizer/index.html?set=train&c=%2Fm%2F0dzct&id=769bb77259bd85d2
faces.jpg:
	$(call download_image,$@,"https://farm3.staticflickr.com/4109/5031905069_cd67b182e3_o.jpg","e23cef02664a28c9c8523a7889b6ff9b")

# License: https://creativecommons.org/licenses/by/2.0/
# https://storage.googleapis.com/openimages/web/visualizer/index.html?set=train&c=%2Fm%2F0h23m&id=d7b9e42392fc7998
sparrow.jpg:
	$(call download_image,$@,"https://c1.staticflickr.com/1/542/19730052293_4e9bede5d0_o.jpg","3c0a157b55daaf87dbab7145072226f0")

# License: https://creativecommons.org/licenses/by/2.0/
# https://storage.googleapis.com/openimages/web/visualizer/index.html?set=train&c=%2Fm%2F01h3n&id=618074321d59d0d8
bee.jpg:
	$(call download_image,$@,"https://c1.staticflickr.com/3/2911/13993945720_95a938e5cf_o.jpg","13b855c8f32727929393ed0eb2a89525")

# License: https://creativecommons.org/licenses/by/2.0/
# https://storage.googleapis.com/openimages/web/visualizer/index.html?set=train&c=%2Fm%2F0jqgx&id=7bf5c5c8b0f4f293
lily.jpg:
	$(call download_image,$@,"https://farm4.staticflickr.com/4110/5099896296_2e2617a0a8_o.jpg","b3b94395f631f2f5ded9299bc46c39a4")

clean:
	rm -f *.jpg
