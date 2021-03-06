from setuptools import setup

setup(name='scorer-to-usebio',
      version='0.3',
      description='Converts from Bridge NZ Scorer format to USEBIO 1.2',
      url='https://github.com/duaneg/scorer-to-usebio',
      author='Duane Griffin',
      author_email='duaneg@dghda.com',
      license='GNU AGPLv3+',
      packages=['scorer_to_usebio'],
      include_package_data=True,
      entry_points={
          'console_scripts': [
              'scorer_to_usebio = scorer_to_usebio.__main__:main',
              'ScorerConverter = scorer_to_usebio:gui',
          ],
      },
      test_suite='nose.collector',
      tests_require=['nose'],
      zip_safe=True
     )
