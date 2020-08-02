from distutils.core import setup

setup(
  name = 'psutil-mqtt',
  packages = ['psutil-mqtt'], 
  version = '0.1.1',
  license='MIT', 
  description = 'Publish hardware monitoring data from psutil to a MQTT broker.',  
  author = 'Jamie Begin',
  author_email = 'jjbegin@gmail.com',
  url = 'https://github.com/jamiebegin/psutil-mqtt', 
  download_url = 'https://github.com/jamiebegin/psutil-mqtt/archive/v0.1.1.tar.gz', 
  keywords = ['mqtt', 'psutil', 'metrics'], 
  setup_requires = [
    wheel
    ],
  install_requires=[ 
          'jsons',
          'psutil',
          'paho-mqtt',
      ],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Information Technology', 
    'Topic :: System :: Monitoring',
    'Topic :: System :: Logging',
    'Topic :: System :: Systems Administration',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
  ],
)