#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

cd nflpredictor
npm install
npm run build

python manage.py collectstatic --noinput
python manage.py migrate --noinput
