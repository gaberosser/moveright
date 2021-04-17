# moveright
## Setup
- Install MongoDB following [these instructions](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/):
```
wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list
apt-get update
apt-get install -y mongodb-org
systemctl start mongod
```
- Install pyenv following [these instructions](https://www.liquidweb.com/kb/how-to-install-pyenv-on-ubuntu-18-04/):
```
apt install -y make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl

git clone https://github.com/pyenv/pyenv.git ~/.pyenv

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n eval "$(pyenv init -)"\nfi' >> ~/.bashrc
pyenv install --list
pyenv install <VERSION>
pyenv global <VERSION>
```
- Setup pipenv:
```
pip install pipenv
cd /path/to/moveright
pipenv install
```
- Add worker job to crontab:
```
crontab -e
# add the following line:
0 1 * * * cd ~/moveright && PYTHONPATH=. pipenv run python bin/get_rightmove_property_for_sale.py
```