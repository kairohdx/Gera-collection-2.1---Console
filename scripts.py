import subprocess


def install():
    subprocess.run("python3 -m venv venv", shell=True)
    subprocess.run("venv/bin/activate && pip install -r requirements.txt -qq", shell=True)

def reqs():
    subprocess.run("venv/bin/activate && pipreqs . --force", shell=True)

def start():
    subprocess.run("venv/bin/activate && python run.py", shell=True)
