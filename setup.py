from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
   name='anki-addon-cardscheduler',
   version='0.0.1',
   description='Anki add-on to schedule cards based on existing knowledge',
   author='Jonathan Schoreels',
   author_email='jonathan.schoreels@gmail.com',
   packages=['leechdetector'],  #same as name
   install_requires=requirements, #external packages as dependencies
)