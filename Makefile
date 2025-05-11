run:
	poetry run python -m app.main

update-anime:
	poetry run python -m tools.update_anime

build:
	poetry run nuitka --enable-plugin=tk-inter --macos-create-app-bundle --follow-imports --onefile --disable-console --windows-icon-from-ico=assets/icon.png --macos-app-icon=assets/icon.png --output-filename=GOTPoll --include-data-dir=assets=assets app/main.py 