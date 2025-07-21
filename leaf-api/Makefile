help: ## show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%s\033[0m|%s\n", $$1, $$2}' \
	| column -t -s '|'


run: # run the app (dev mode)
	uvicorn app:app --reload --host 0.0.0.0

requirements: ## install requirements
	pip install -r requirements.txt