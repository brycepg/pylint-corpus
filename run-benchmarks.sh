set -euo pipefail
(cd ~/astroid && git checkout master)
pytest --benchmark-save=master
(cd ~/astroid && git checkout nickdrozd/speed)
pytest --benchmark-save=nickdrozd
