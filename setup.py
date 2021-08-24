from setuptools import setup

setup(
    name='prettymaps',
    version='1.0.0',    
    description='A simple python library to draw pretty maps from OpenStreetMap data',
    url='https://github.com/marceloprates/prettymaps',
    author='Marcelo Prates',
    author_email='marceloorp@gmail.com',
    license='MIT License',
    packages=['prettymaps'],
    install_requires=[
        'osmnx==1.0.1',
        'tabulate==0.8.9',
        'jupyter==1.0.0',
        #'vsketch==1.0.0'
    ],

    classifiers=[
        'Intended Audience :: Science/Research',
    ],
)    
