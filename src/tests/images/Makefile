# Open Images Dataset V4
all: cat.jpg dog.jpg hotdog.jpg faces.jpg

# License: https://creativecommons.org/licenses/by/2.0/
# URL: https://storage.googleapis.com/openimages/web/visualizer/index.html?set=train&c=%2Fm%2F01yrx&id=818c36d0b603e096
cat.jpg:
	wget -O $@ "https://farm7.staticflickr.com/3712/11270364836_8d1182be97_o.jpg"
	echo f08083ddb111a9d5bd6e00d7c04aa97f $@ | md5sum --check -

# License: https://creativecommons.org/licenses/by/2.0/
# URL: https://storage.googleapis.com/openimages/web/visualizer/index.html?set=train&c=%2Fm%2F0bt9lr&id=b2e6af69191eb3bf
dog.jpg:
	wget -O $@ "https://c8.staticflickr.com/8/7580/15865399370_3857b60669_o.jpg"
	echo 416afbfd4bd09758955cdffa2e62a58e $@ | md5sum --check -

# License: https://creativecommons.org/licenses/by/2.0/
# URL: https://storage.googleapis.com/openimages/web/visualizer/index.html?set=train&c=%2Fm%2F01b9xk&id=4d7133d6aabede44
hotdog.jpg:
	wget -O $@ "https://farm5.staticflickr.com/7284/16301478750_b036c617cb_o.jpg"
	echo cc466191c0844c8da25bbbf63b66bd15 $@ | md5sum --check -

# License: https://creativecommons.org/licenses/by/2.0/
# URL: https://storage.googleapis.com/openimages/web/visualizer/index.html?set=train&c=%2Fm%2F0dzct&id=769bb77259bd85d2
faces.jpg:
	wget -O $@ "https://farm3.staticflickr.com/4109/5031905069_cd67b182e3_o.jpg"
	echo e23cef02664a28c9c8523a7889b6ff9b $@ | md5sum --check -

clean:
	rm -f *.jpg