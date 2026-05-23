.PHONY: help setup generate run test demo dashboard lint deploy post_deploy destroy clean

help:
	@echo "Targets:"
	@echo "  setup       install python dependencies"
	@echo "  generate    write synthetic source extracts to data/landing/"
	@echo "  run         build Bronze -> Silver -> Gold (local DuckDB runner)"
	@echo "  test        run data-quality tests against Gold"
	@echo "  dashboard   launch the Streamlit dashboard"
	@echo "  demo        generate + run + dashboard"
	@echo "  lint        sqlfluff lint of sql/"
	@echo "  deploy      deploy Azure infra (Bicep, subscription-scoped)"
	@echo "  post_deploy seed Key Vault + wire ADF"
	@echo "  destroy     delete the Azure resource group"
	@echo "  clean       remove generated data artifacts"

setup:
	pip install -r requirements.txt

generate:
	python -m src.generators.generate_all

run:
	python -m src.pipelines.local_run

test:
	pytest -q

demo: generate run dashboard

dashboard:
	streamlit run bi/dashboard/app.py

lint:
	sqlfluff lint sql/ --dialect databricks || true

deploy:
	./scripts/deploy.sh

post_deploy:
	./scripts/post_deploy.sh

destroy:
	./scripts/teardown.sh

clean:
	rm -rf data/landing data/bronze data/silver data/gold
