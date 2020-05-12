# Securelink

## Running locally
To install the dependencies, run:
```sh
pip install -r requirements.txt
```

To run the app, run:
```sh
FLASK_ENV=development python run.py
```

## Deployment

First, make sure that you have the ssh alias ``dokku-stack-public`` defined.

In each newly-cloned repo, add a git remote:

```sh
git remote add dokku dokku@dokku-stack-public:securelink
```

Now you can push to deploy:

```sh
git push dokku master
```
