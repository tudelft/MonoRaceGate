# Download Data



all: season1.zip
	unzip season1.zip
	python ./generate_masks.py


clean:
	rm -rf season1.zip
	rm -rf ./data/*/img_*.*
	rm -rf ./data/*/check_*.*
	rm -rf ./data/*/mask_*.*

season1.zip:
	wget https://github.com/tudelft/MonoRaceGate/releases/download/v1.0.0/season1.zip


zip:
	zip -r season1.zip . -i '*.jpg' '*.png'
	find . -type f -name "*.png" -delete
	find . -type f -name "*.jpg" -delete
