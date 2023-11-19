connect to server

[//]: # (ssh -i ./python_key.pem ubuntu@65.2.30.207)
ssh -i "python_key.pem" ec2-user@ec2-13-232-23-156.ap-south-1.compute.amazonaws.com

http://ec2-13-232-23-156.ap-south-1.compute.amazonaws.com:8000/

update libs
sudo apt update
sudo apt upgrade

Install Python:
Ubuntu typically comes with Python 3 pre-installed. To check your Python version:
python3 --version

If Python 3 is not installed, you can install it using the package manager:
sudo apt install python3

Installing pip:
pip is a package manager for Python. You should install it if it's not already present:
sudo apt install python3-pip

Check the installed version:
pip3 --version

[//]: # (we need to do this to link github account with server so we can clone code)

Generate an SSH Key on Your Server:
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

Display the Public Key:
cat ~/.ssh/id_rsa.pub

Grant Repository Access:
To use this deploy key with a specific repository, follow these steps:
Go to the repository on GitHub.
Click on "Settings" in the top right.
In the left sidebar, click on "Deploy keys."
Click on "Add deploy key."
Give the key a title.
Paste your public key into the "Key" field.
Check the "Allow write access" option if your deployment process requires write access to the repository (e.g., for pushing changes).
Click "Add key."

clone repository
git clone git@github.com:shaileshBhokare/bn-level-watcher.git

move to project folder
cd bn-level-watcher/

install project libs
pip3 install -r requirements.txt

run project -> 
flask run --host=0.0.0.0 --port=5000

http://<server-ip>:5000

pm2 start app.py --name "flask-app"
sudo pm2 start app.py --name "flask-app" --output ./logs/out.log --error ./logs/error.log

sudo pm2 start app.py --name "flask-app" --interpreter python3 --output ./logs/out.log --error ./logs/error.log


python3 -m venv venv

source venv/bin/activate
pip3 install --upgrade setuptools
python3 -m pip install --upgrade pip
pip3 install -r requirements.txt

pm2 logs "flask-app" --lines 100

nohup python3 app.py &

ps aux | grep app.py

kill pid
